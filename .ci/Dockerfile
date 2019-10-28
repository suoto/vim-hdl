# Xenial: 16.04.6
# Trusty: 14.04.6
# Bionic beaver: 18.04.3
# FROM ubuntu:14.04
# FROM ubuntu:16.04
FROM ubuntu:18.04

ENV DEBIAN_FRONTEND noninteractive

ENV GHDL_HOST="http://downloads.sourceforge.net/project/ghdl-updates/Builds"
ENV GHDL_URL="${GHDL_HOST}/ghdl-0.33/ghdl-0.33-x86_64-linux.tgz"
ENV COLUMNS=80
ENV LINES=50

ENV VROOM_VERSION=95c0b9140c610524155adb41a1d1dd686582d130 

ENV PACKAGES="\
  autoconf      \
  automake      \
  cmake         \
  g++           \
  gettext       \
  git           \
  libgnome2-dev \
  libgtk2.0-dev \
  libtool       \
  libtool-bin   \
  ninja-build   \
  python        \
  python3       \
  pkg-config    \
  unzip         \
  vim-gnome     \
  wget          \
  xvfb"

# Install packages
RUN apt-get update                                          && \
  apt-get install --yes --no-install-recommends $PACKAGES

RUN apt-get install --yes python3-pip python-pip

RUN pip3 install "git+https://github.com/google/vroom@$VROOM_VERSION"
RUN pip3 install vim-vint==0.3.15
RUN pip3 install neovim==0.3.1

RUN git clone --quiet --recursive --depth 1 --branch=hdlcc_ci \
    https://github.com/suoto/hdlcc_ci ../hdlcc_ci

# Download GHDL
ENV INSTALLATION_DIR="/builders/ghdl/"
RUN mkdir -p "${INSTALLATION_DIR}"
RUN wget "${GHDL_URL}" -O "ghdl.tar.gz" &&  \
  tar zxvf "ghdl.tar.gz" --directory "${INSTALLATION_DIR}" && \
  rm "ghdl.tar.gz" && \
  "${INSTALLATION_DIR}"/bin/ghdl --version

RUN apt-get autoclean                           && \
  apt-get --auto-remove purge                   && \
  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PATH=/builders/ghdl/bin/:${PATH}
RUN ghdl --version

WORKDIR /data
VOLUME ["/data"]
 
# RUN xvfb-run --server-args='-screen 0, 1024x768x24' -e /dev/stdout 
#     ./run_tests.sh --log-capture -F
# # Export the output data
