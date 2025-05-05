# This file is part of the C+ project.
#
# Copyright (C) 2025 GiladLeef
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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