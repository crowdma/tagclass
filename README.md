
<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/crowdma/tagclass">
  </a>

  <h3 align="center">TagClass</h3>

  <p align="center">
    A Tool for Extracting Class-determined Tags from Massive Malware Labels
    <br />
    <a href="https://github.com/crowdma/tagclass/issues">Report Bug</a>
    ·
    <a href="https://github.com/crowdma/tagclass/issues">Request Feature</a>
  </p>
</div>



<!-- ABOUT THE PROJECT -->
## Abstract

VirusTotal is widely used for malware annotation by providing malware labels from a large set of anti-malware engines. A long-standing challenge in using these inconsistent labels is extracting class-determined tags. In this paper, we present TagClass, a tool based on incremental parsing to associate tags with their corresponding family, behavior, and platform classes. TagClass treats behavior and platform tags as locators and achieves incremental parsing by introducing and iterating the following two algorithms: 1) location first search, which hits family tags using locators, and 2) co-occurrence first search, which finds new locators by family tags. Experiments across two benchmark datasets indicate TagClass outperforms existing methods, improving the parsing accuracy by 21% and 28%, respectively. To the best of our knowledge, TagClass is the first tag class-determined malware label parsing tool, which would pave the way for research on crowdsourcing malware annotation. TagClass has been released to the community.

<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

TagClass uses [Poetry](https://python-poetry.org/docs/) for dependency management and packaging in Python. Please install it first according to its official documentation.

### Installation

- Run the following commands:
   ```sh
   git clone https://github.com/crowdma/tagclass.git
   cd tagclass
   poetry install
   pytest
   ```



<!-- USAGE EXAMPLES -->
## Usage

- Help
    ```sh
    $ tagclass --help

    Usage: tagclass [OPTIONS] COMMAND [ARGS]...

    ╭─ Options ───────────────────────────────────────────────────────╮
    │ --help          Show this message and exit.                     │
    ╰─────────────────────────────────────────────────────────────────╯
    ╭─ Commands ──────────────────────────────────────────────────────╮
    │ clean          Clean pending vocabulary                         │
    │ evaluate       Evaluation for TagClass                          │
    │ list           List vocabulary                                  │
    │ parse          Location first search wrapped parsing            │
    │ tokenize       Tokenize malware label                           │
    │ update         Incremental parsing wrapped updating             │
    │ version        TagClass version                                 │
    ╰─────────────────────────────────────────────────────────────────╯
    ```

- Location first search (LFS) wrapped parsing
    ```sh
    $ tagclass parse --label Ransom.Win32.Cerber
    [
        Result(tag='ransom', entity='behavior', score=10),
        Result(tag='win', entity='platform', score=10),
        Result(tag='cerber', entity='family', score=8)
    ]
   ```
- Evaluation

    ```sh
    $ tagclass evaluate parse --malgenome
    Reading... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.4/8.4 MB 0:00:00
    [*] ============ Acc of Euphony scope ============
        malgenome labels = 6661
        Euphony scope = 4361
        Euphony success but Tagclass failed = 17
        Tagclass failed in the Scope of Euphony = 33
        Euphony Acc = 0.7706947947718413
        Tagclass Acc = 0.9924329282274708
        =============================================
    [*] ============= Acc of all labels =============
        malgenome labels = 6661
        Tagclass failed  = 104
        Tagclass Acc = 0.9843867287194115
        =============================================
    ```

<!-- LICENSE -->
## License

Distributed under the MIT License.