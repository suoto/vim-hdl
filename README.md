# vim-hdl

vim-hdl is a Vim plugin that provides some helpers to VHDL development:

* Syntax checking (using
  [third-party-compilers](#supported-third-party-compilers) +
  [Syntastic][Syntastic])
* [CTags indexing](#supported-tag-generators)

![vim-hdl screenshot](http://i.imgur.com/YksSZq0.png)

## Installation

### [Pathogen][pathogen]

```bash
cd ~/.vim/bundle/
git clone https://github.com/suoto/vim-hdl.git
```

### [Vundle][vundle]

In your .vimrc:

```viml
Plugin 'suoto/vim-hdl'
```

### Notes

* Requires Vim compiled with Python support, plus features needed by
  [Syntastic][Syntastic] itself
* Only tested on Linux with recent Vim versions (7.4+)

## Usage

vim-hdl requires a configuration file listing libraries, source files,
build flags, etc. Select the configuration file via

```viml
let g:vimhdl_conf_file = '<config/file>'
```

The configuration file syntax follows Python [ConfigParser][ConfigParser].

Any other [Syntastic][Syntastic] option should work as well.

You can clone [vim-hdl-examples][vim-hdl-examples] repository and try a ready-to-use
setup.

## Supported third-party compilers

* [Mentor Graphics® ModelSim®][MG_msim]
* [ModelSim-Altera® Edition][Altera_msim]

Currently there are no plans to support other simulators/compilers.

## Supported tag generators

* [Ctags][ctags]

Currently there are no plans to support other tag generators.

## Issues

You can use the [issue tracker][issue_tracker] for bugs, feature request and so on.

## License

This software is licensed under the [GPL v3 license][gpl].

## Notice

Mentor Graphics®, ModelSim® and their respective logos are trademarks or registered
trademarks of Mentor Graphics, Inc.

Altera® and its logo is a trademark or registered trademark of Altera Corporation.

vim-hdl's author has no connection or affiliation to any of the trademarks mentioned
or used by this software.

[Syntastic]: https://github.com/scrooloose/syntastic
[MG_msim]: http://www.mentor.com/products/fv/modelsim/
[Altera_msim]: https://www.altera.com/downloads/download-center.html
[pathogen]: https://github.com/tpope/vim-pathogen
[vundle]: https://github.com/VundleVim/Vundle.vim
[ConfigParser]: https://docs.python.org/2/library/configparser.html
[vim-hdl-examples]: https://github.com/suoto/vim-hdl-examples
[gpl]: http://www.gnu.org/copyleft/gpl.html
[issue_tracker]: https://github.com/suoto/vim-hdl/issues
[ctags]: http://ctags.sourceforge.net/

