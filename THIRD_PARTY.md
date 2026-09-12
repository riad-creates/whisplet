# Third-party models and runtimes

Phonon does not commit model weights to this repository. The public release
downloads Parakeet directly from its upstream Hugging Face repository.

## uv

- Source: <https://github.com/astral-sh/uv>
- License: Apache-2.0 OR MIT

The signed DMG bundles the arm64 `uv` executable so a clean Mac can create the
local Python environment used by Parakeet. Model weights and Python packages are
still downloaded into the user's normal caches on first launch.

## Parakeet TDT 0.6B v2

The experimental `sidecar/dictionary_bias.py` final-transcript decoder adapts the greedy TDT loop from [parakeet-mlx 0.5.2](https://github.com/senstella/parakeet-mlx), licensed Apache-2.0. Its license is retained at [third_party/parakeet-mlx/LICENSE](third_party/parakeet-mlx/LICENSE) and bundled under `Contents/Resources/licenses/parakeet-mlx/`. Changes add dictionary prefix tracking, bounded token bonuses, and original-distribution confidence calculation in float32. This is a custom experiment, not NVIDIA's GPU-PB implementation.

- Source: <https://huggingface.co/mlx-community/parakeet-tdt-0.6b-v2>
- Upstream model: NVIDIA Parakeet TDT 0.6B v2
- License: CC-BY-4.0
- Primary weight: `model.safetensors`
- Size: 2,471,559,904 bytes
- SHA-256: `b958c37a6baa6874a279108755c8f2818e27bf647d72d54800a234a421341dfe`

## S1-mini by Superwhisper

- Original model and documentation: https://huggingface.co/superwhisper/s1-mini
- MLX 4-bit conversion: https://huggingface.co/mlx-community/S1-mini-MLX-4bit
- Pinned conversion revision: `5cbd7aec3401144f88a331d385c40b65fd2548eb`
- License: Apache 2.0 with an additional model-name and attribution term.
- Full license: [third_party/s1-mini/LICENSE](third_party/s1-mini/LICENSE), also bundled in the app under `Contents/Resources/licenses/s1-mini/`.

This integration identifies the model as **S1-mini by Superwhisper**. The MLX conversion is provided by mlx-community. Model weights download into the Hugging Face cache and are not committed or included in the app bundle.

## Fluid-1

The following FluidVoice entry describes the optional legacy developer benchmark only, not this build's normal cleanup pipeline.

- Source: <https://huggingface.co/ALTICDEV/FLUID-1>
- License: AGPL-3.0
- Primary weight: `model-Q4_K_M.gguf`
- Size: 2,497,280,160 bytes
- SHA-256: `619dca002c4a2bf683311a6084c75ba31ab610b9b352720f9ead9e9bceac7590`

FluidVoice itself is GPL-3.0, but its release-only `fluid-intelligence-mlx`
provider is not present in the public FluidVoice source. Phonon does not
redistribute that helper. Fluid-1 is documented here for the optional correction
integration; it is not downloaded by the baseline Homebrew release.

## llama.cpp

- Source: <https://github.com/ggml-org/llama.cpp>
- License: MIT

If llama.cpp is added to a future binary release, its exact revision and notice
must be included in that release.
