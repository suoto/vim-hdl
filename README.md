# vim-hdl

vim-hdl is a Vim plugin that uses [`hdlcc`][hdlcc] to provide some helpers to VHDL
development:

* Syntax checking using [Syntastic][Syntastic] along with third-party compilers
 supported by `hdlcc`. (see [`hdlcc`'s README]
 (https://github.com/suoto/hdlcc#supported-third-party-compilers) for an updated
 list)
* [Style checking](#style-checking)

![vim-hdl screenshot](http://i.imgur.com/YksSZq0.png)

---

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

---

## Usage

vim-hdl requires a configuration file listing libraries, source files,
build flags, etc. Select the configuration file via

```viml
let g:vimhdl_conf_file = '<config/file>'
```

See the [wiki](https://github.com/suoto/vim-hdl/wiki#project-file-formats) for
details on how to write it.

Any other [Syntastic][Syntastic] option should work as well.

You can clone [vim-hdl-examples][vim-hdl-examples] repository and try a ready-to-use
setup.

---

## Issues

You can use the [issue tracker][issue_tracker] for bugs, feature request and so on.

## License

This software is licensed under the [GPL v3 license][gpl].

## Notice

Mentor Graphics®, ModelSim® and their respective logos are trademarks or registered
trademarks of Mentor Graphics, Inc.

Altera® and its logo is a trademark or registered trademark of Altera Corporation.

Xilinx® and its logo is a trademark or registered trademark of Xilinx, Inc.

vim-hdl's author has no connection or affiliation to any of the trademarks mentioned
or used by this software.

[Syntastic]: https://github.com/scrooloose/syntastic
[Mentor_msim]: http://www.mentor.com/products/fv/modelsim/
[Altera_msim]: https://www.altera.com/downloads/download-center.html
[Xilinx_Vivado]: http://www.xilinx.com/products/design-tools/vivado/vivado-webpack.html
[pathogen]: https://github.com/tpope/vim-pathogen
[vundle]: https://github.com/VundleVim/Vundle.vim
[ConfigParser]: https://docs.python.org/2/library/configparser.html
[vim-hdl-examples]: https://github.com/suoto/vim-hdl-examples
[gpl]: http://www.gnu.org/copyleft/gpl.html
[issue_tracker]: https://github.com/suoto/vim-hdl/issues
[hdlcc]: https://github.com/suoto/hdlcc
