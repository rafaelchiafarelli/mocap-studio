# 31. The shared file can't be zoomed or moved

**Symptom:** in the Blender file, Rafael can't zoom or move the camera.
**Where:** not confirmed, Blender was only run without a window. The saved views aren't locked. Two likely causes: the view's pivot is at the origin while the bodies start at X = 18 m (`human-model/blender/shared_file.py`, strip numbers kept after removing runs), and `review\fast_review_todas.blend` holds 26.7 million triangles in 2,046 meshes, before the skins' two subdivision levels.
**Impact:** the file can't be reviewed.
**Status:** Open
