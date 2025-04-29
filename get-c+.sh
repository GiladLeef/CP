

URL="https://github.com/GiladLeef/CP"
OUTPUT_DIR="/home/$USER/.cplang"
OUT_LINK="/home/$USER/.local/bin/c+"
install()
{
    rm -rf $OUTPUT_DIR
    rm $OUT_LINK
    git clone $URL $OUTPUT_DIR
    export CP_DIR=$OUTPUT_DIR
    ln $OUTPUT_DIR/bin/c+.sh $OUT_LINK
}
install
echo "Successfully installed"
echo "Use 'c+' for compiling files"