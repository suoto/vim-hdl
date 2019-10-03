FROM tweekmonster/vim-testbed:latest

RUN install_vim -tag v8.0.0027 -build \
                -tag v8.1.0519 -build \
                -tag neovim:v0.2.0 -build \
                -tag neovim:v0.3.5 -build

ENV PACKAGES=" \
    bash       \
    git        \
    python3    \
    py3-pip    \
    wget       \
"

RUN apk --update add $PACKAGES && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

RUN git clone https://github.com/google/vroom             && \
    cd vroom                                              && \
    git checkout 95c0b9140c610524155adb41a1d1dd686582d130 && \
    pip3 install -e .

RUN pip3 install vim-vint==0.3.15



# RUN pip3 install hdl-checker==0.6
