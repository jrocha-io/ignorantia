# IEEE citation style

Used in computer science, electrical engineering, math, physics, and most exact-sciences journals/conferences. Citations are numbered in order of first appearance, in square brackets `[1]`, `[2,3]`, `[4–6]`. The reference list is in **citation order, not alphabetical**.

## In-text

- Single: `as shown in [3]`
- Multiple: `[1], [4], [9]` (each in its own brackets, comma-separated)
- Range: `[2]–[5]`
- Citation as noun: `Reference [3] showed...` (not "[3] showed...")

## Reference list — formats by source type

### Journal article

```
[N] A. Author, B. Author, and C. Author, "Article title in sentence case," 
    Journal Name in Title Case, vol. X, no. Y, pp. Z–W, Month Year, 
    doi: 10.xxxx/yyyy.
```

Example:
```
[1] J. Smith, "Transformer architectures for time-series anomaly detection," 
    IEEE Trans. Neural Netw. Learn. Syst., vol. 34, no. 7, pp. 3211–3225, 
    Jul. 2023, doi: 10.1109/TNNLS.2023.1234567.
```

Note: journal names are abbreviated per IEEE's standard list (e.g., *IEEE Transactions on Neural Networks and Learning Systems* → *IEEE Trans. Neural Netw. Learn. Syst.*).

### Conference paper

```
[N] A. Author and B. Author, "Paper title," in Proc. Conf. Name Abbrev., 
    City, Country, Year, pp. X–Y, doi: 10.xxxx/yyyy.
```

Example:
```
[2] M. Lee et al., "GamifyEdu: a framework for educational game design," 
    in Proc. ACM SIGCSE, Toronto, Canada, 2024, pp. 145–151, 
    doi: 10.1145/3626252.3630855.
```

### Book

```
[N] A. Author, Book Title in Title Case, Xth ed. City: Publisher, Year, ch. Z.
```

### Book chapter

```
[N] A. Author, "Chapter title," in Book Title, Xth ed., B. Editor, Ed. 
    City: Publisher, Year, pp. M–N.
```

### Online resource / report

```
[N] A. Author, "Title," Org., City, Rep. No., Year. [Online]. 
    Available: https://url
```

### Preprint (arXiv)

```
[N] A. Author and B. Author, "Title," 2024, arXiv:2401.12345.
```

### Thesis

```
[N] A. Author, "Title," Ph.D. dissertation, Dept., Univ., City, Year.
```

### Standard

```
[N] Title of Standard, Standard Number, Year.
```

## Author name format

- Initial + period + space + family name: `A. B. Smith`
- 6 or fewer authors: list all.
- More than 6 authors: list first 3, then `et al.` — `A. Author et al.`

## Title case

- Article and chapter titles: **sentence case** with quotes.
- Journal, conference, and book names: **title case** in italics (or just italics in plaintext).

## DOI

- Always include DOI when available, formatted as `doi: 10.xxxx/yyyy` (lowercase "doi:").

## BibTeX

For LaTeX, IEEE's official `IEEEtran.cls` + `IEEEtran.bst` (BibTeX style) handle formatting automatically:

```latex
\documentclass[conference]{IEEEtran}
% in body
\bibliographystyle{IEEEtran}
\bibliography{refs}
```

Always recommend to the user to download `IEEEtran.cls` from CTAN: https://mirrors.ctan.org/macros/latex/contrib/IEEEtran/.
