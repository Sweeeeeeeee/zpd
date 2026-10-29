# Atsauces / References

## Papers

1. A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez,
   Ł. Kaiser, I. Polosukhin. *Attention Is All You Need.* NeurIPS 2017.
   arXiv:1706.03762. The transformer architecture behind `geo-lm`.
2. A. Radford, J. Wu, R. Child, D. Luan, D. Amodei, I. Sutskever. *Language
   Models are Unsupervised Multitask Learners* (GPT-2). OpenAI, 2019. The
   decoder-only layout and weight initialisation used in `geo-lm`.
3. T. H. Trinh, Y. Wu, Q. V. Le, H. He, T. Luong. *Solving olympiad geometry
   without human demonstrations* (AlphaGeometry, "AG1"). Nature 625, 476–482
   (2024). doi:10.1038/s41586-023-06747-5. The DDAR + language model approach.
4. Y. Chervonyi, T. H. Trinh, M. Olšák, X. Yang, H. Nguyen, M. Menegali, J. Jung,
   V. Verma, Q. V. Le, T. Luong. *Gold-medalist Performance in Solving Olympiad
   Geometry with AlphaGeometry2* ("AG2"). arXiv:2502.03544 (2025).
5. V. Sicca et al. *Newclid: A User-Friendly Replacement for AlphaGeometry.*
   arXiv:2411.11938 (2024). The DDAR engine used here.
6. M. Zhu, Z. Wang, et al. *GenesisGeo: Technical Report.* arXiv:2509.21896
   (2025). Source of the training data.
7. S.-C. Chou, X.-S. Gao, J.-Z. Zhang. *A Deductive Database Approach to
   Automated Geometry Theorem Proving and Discovering.* Journal of Automated
   Reasoning 25, 219–246 (2000). The deductive database (DD) method.
8. A. Paszke et al. *PyTorch: An Imperative Style, High-Performance Deep
   Learning Library.* NeurIPS 2019. arXiv:1912.01703.

## Software and data

| what | where | used for |
|---|---|---|
| Newclid 3.0.1 + py-yuclid 3.0.0 | https://github.com/Newclid/Newclid (formerly LMCRC/Newclid), PyPI `newclid[yuclid]` | DDAR engine, rules, constructions, example problems |
| GenesisGeo dataset | https://huggingface.co/datasets/ZJUVAI/GenesisGeo (Apache-2.0) | 100k training examples (step 4) |
| GenesisGeo code | https://github.com/ZJUVAI/GenesisGeo | checked for reusable generation code |
| AlphaGeometry (DeepMind) | https://github.com/google-deepmind/alphageometry | original DDAR; not used (needs Meliad) |
| PyTorch | https://pytorch.org | model and training |
