"""Smoke tests v2.8.0 — validação mecânica das Decisões 19, 30, 33.

Decisão 19: anti-vazamento de meta-discurso do skill nos templates do manuscrito.
Decisão 30: feature "rabiscos for fun" removida do código ativo.
Decisão 33: identidade da skill protegida (default da `interface` no AI disclosure).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_decision_19_template_has_no_skill_branding():
    """Template HTML do manuscrito não contém 'ignorantia' como brand visível ao leitor."""
    template = (ROOT / "assets" / "templates" / "manuscript-template.html").read_text(encoding="utf-8")
    # Verifica nas regiões críticas do template — title, meta generator, topbar brand, footer brand.
    title_match = re.search(r"<title>([^<]+)</title>", template)
    assert title_match, "template não tem <title>"
    assert "ignorantia" not in title_match.group(1).lower(), (
        "VIOLAÇÃO Decisão 19: <title> contém 'ignorantia'"
    )
    meta_match = re.search(r'<meta\s+name="generator"\s+content="([^"]+)"', template)
    if meta_match:
        # se existir meta generator, não pode citar o skill por nome
        content = meta_match.group(1).lower()
        assert "ignorantia" not in content, (
            "VIOLAÇÃO Decisão 19: meta generator contém 'ignorantia'"
        )
    # Topbar e footer não devem ter o nome do skill em texto visível
    # (atenção: o conteúdo de variáveis like {{TITLE_SHORT}} é seguro porque
    # vem do protocolo do usuário, não da skill).
    visible_brand_pattern = re.compile(r'<div class="brand"[^>]*>\s*ignorantia\s*<', re.IGNORECASE)
    assert not visible_brand_pattern.search(template), (
        "VIOLAÇÃO Decisão 19: brand do topbar contém 'ignorantia'"
    )
    footer_brand_pattern = re.compile(r'<footer>.*?<strong>\s*ignorantia\s*</strong>', re.DOTALL | re.IGNORECASE)
    assert not footer_brand_pattern.search(template), (
        "VIOLAÇÃO Decisão 19: footer contém 'ignorantia' como brand"
    )


def test_decision_19_render_manuscript_default_interface_is_protected():
    """O default do campo 'interface' no AI disclosure não revela nome do skill (Decisão 33)."""
    src = (ROOT / "scripts" / "render_manuscript.py").read_text(encoding="utf-8")
    # O default antigo era "ignorantia v..."; o novo é "algoritmo particular do autor..."
    # Procurar o trecho do disclosure especificamente
    assert "ai.get('interface', 'ignorantia v'" not in src, (
        "VIOLAÇÃO Decisão 33: render_manuscript ainda usa default 'ignorantia v...' no AI disclosure"
    )
    assert "algoritmo particular do autor" in src, (
        "VIOLAÇÃO Decisão 33: default protegido do AI disclosure não está em render_manuscript"
    )


def test_decision_30_fun_doodles_builder_is_stub():
    """A função build_fun_doodles_html foi reduzida a stub que retorna string vazia."""
    # Importa direto do módulo
    sys.path.insert(0, str(ROOT / "scripts"))
    import render_manuscript

    # Mesmo com input não-vazio, deve retornar ""
    sample_doodles = [
        {"text": "TOP!", "type": "exclaim", "anchor_selector": "#x"},
        {"text": "OLHA!", "type": "exclaim", "anchor_selector": "#y"},
    ]
    result = render_manuscript.build_fun_doodles_html(sample_doodles)
    assert result == "", (
        f"VIOLAÇÃO Decisão 30: build_fun_doodles_html não é stub; retornou {result!r}"
    )
    # E também com input vazio
    assert render_manuscript.build_fun_doodles_html([]) == ""
    assert render_manuscript.build_fun_doodles_html(None) == ""


def test_decision_30_skill_md_does_not_describe_fun_doodles():
    """SKILL.md não descreve mais a feature em texto ativo (apenas no histórico de Decisão 30)."""
    skill_md = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    # A menção a "fun_doodles", "rabiscos for fun", "TOP VOICE", "Permanent Marker"
    # só deve aparecer no contexto da Decisão 30 (que documenta a remoção).
    # Heurística: se aparecer fora desse contexto, é vazamento.
    forbidden_terms_in_active_text = ["TOP VOICE", "Permanent Marker"]
    for term in forbidden_terms_in_active_text:
        # Permitido APENAS se vier dentro de bloco de Decisão 30
        idx = skill_md.find(term)
        if idx == -1:
            continue
        # Verificar se esse índice está dentro do bloco da Decisão 30
        decision_30_start = skill_md.find("### Decisão 30")
        decision_30_end = skill_md.find("### Decisão 33")
        if decision_30_start != -1 and decision_30_end != -1:
            if decision_30_start < idx < decision_30_end:
                continue  # ok, está no histórico da Decisão 30
        assert False, (
            f"VIOLAÇÃO Decisão 30: '{term}' aparece em SKILL.md fora do bloco da Decisão 30"
        )


def test_decision_20_persona_block_present_in_skill_md():
    """SKILL.md contém o bloco de Voz autoral padrão (Decisão 20)."""
    skill_md = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "### Decisão 20 — Voz autoral padrão" in skill_md
    # Garantir que blocos críticos estão presentes
    assert "acadêmico neutro impessoal" in skill_md
    assert "ABNT/Vancouver" in skill_md
    assert "IMRaD" in skill_md
    assert "Sem hedging ornamental" in skill_md
    # E especialmente o "O que a persona NÃO faz", que é a cláusula de bloqueio
    assert "não menciona o skill" in skill_md.lower()
