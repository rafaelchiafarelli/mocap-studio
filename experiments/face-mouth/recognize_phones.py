"""Recognizes sounds with Allosaurus, set to Portuguese. Args: wav, output, optional model folder used when the package has none."""
import os, shutil, sys
import allosaurus
from allosaurus.app import read_recognizer
wav, out = sys.argv[1:3]
target = os.path.join(os.path.dirname(allosaurus.__file__), "pretrained", "uni2005")
if len(sys.argv) > 3 and not os.path.isdir(target):
    shutil.copytree(sys.argv[3], target)
open(out, "w", encoding="utf-8").write(read_recognizer("uni2005").recognize(wav, lang_id="por", timestamp=True))
