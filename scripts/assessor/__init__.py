"""
ignorantia.assessor — Sistema modular de avaliação automática.

Módulos:
    eliminators  — Verifica critérios eliminatórios (E1-E11). Retorna fase + alerta.
    rubric       — Aplica rubrica D1-D5 e produz pontuação numérica.
    venues       — Calcula status por venue (🟢/🟡/🟠/🔴).
    plagiarism   — Camada 1 (interna ao corpus).
    report_html  — Gera HTML de auditoria embutível.
    helpers      — Utilitários compartilhados (load CSV/JSON, regex, hashes).

Entry point:
    main.py — orquestra todos os módulos para gerar avaliacao.
"""
__version__ = "2.0.0-alpha26"
