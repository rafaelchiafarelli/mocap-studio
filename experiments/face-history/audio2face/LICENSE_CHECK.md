# Audio2Face test: license check, for the creator to confirm

Read 2026-11-01. This is my reading of the terms, not legal advice. Not yet recorded in `face-audio` prework/2.

| Item | Version | License | Commercial use | Used in this test | Source |
|---|---|---|---|---|---|
| Audio2Face-3D model | v3.0, revision b7413273 | NVIDIA Open Model License (2025-10-24) | Yes: "Models are commercially usable"; NVIDIA claims no ownership of outputs | Yes | huggingface.co/nvidia/Audio2Face-3D-v3.0 |
| Audio2Face SDK source | commit 1ca0f025 | MIT | Yes | Read only, not built; windowing and solver logic reproduced in Python | github.com/NVIDIA/Audio2Face-3D-SDK |
| ONNX Runtime | see requirements_used.txt | MIT | Yes | Yes | pypi.org/project/onnxruntime |
| MediaPipe Face Landmarker | model bundle float16/1 | Apache-2.0 (all three model cards) | Yes | Yes, blink and brows | developers.google.com/edge/mediapipe |
| MPFB Faceunits 01 | pack metadata | CC0 | Yes | Yes, face shapes | static.makehumancommunity.org |
| Audio2Emotion | v2.2 | NVIDIA license limited to the Audio2Face project; forbids emotion recognition | Restricted | **No: not downloaded** | huggingface.co/nvidia/Audio2Emotion-v3.0 |
| CUDA toolkit | 12.9 | NVIDIA proprietary EULA, no fee | No ban found; proprietary | **No: not needed by the Python route** | SDK licenses/cuda-LICENSE.txt |
| TensorRT | 10.13 | NVIDIA proprietary SLA, no fee | No ban found; proprietary | **No: not needed by the Python route** | docs.nvidia.com/deeplearning/tensorrt/sla |

Conditions to respect:
- If the model is ever redistributed, include the notice "Licensed by NVIDIA Corporation under the NVIDIA Open Model License".
- Use must stay consistent with NVIDIA's Trustworthy AI terms.
- The license ends automatically if safety guardrails are bypassed, or for that model if you bring copyright or patent litigation.

Open point: the model card lists multi-speaker English training audio. Portuguese is unconfirmed and must be tested.
