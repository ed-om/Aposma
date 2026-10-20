# Validation status

## Verified in the build environment

- Python source compiles with `python3 -m compileall`.
- Python unit tests pass: `3 passed`.
- Repository structure and scripts are present.

## Not compiled here

The container used for packaging does not have the LLVM/Clang development CMake package (`LLVMConfig.cmake`) installed, so the native analyzer could not be compiled in this environment.

On the target Mint/Ubuntu machine, install a matching LLVM/Clang development toolchain, then run:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

If the distro installs LLVM CMake files outside the default search path, set `LLVM_DIR` and/or `CMAKE_PREFIX_PATH` according to `llvm-config --cmakedir`.
