# GCC built-in header fix

This patch makes the Python analyzer runner discover Clang's resource include directory and GCC's built-in include directory (only when `stddef.h` exists), then pass those paths to Clang LibTooling. This addresses `fatal error: 'stddef.h' file not found` when analyzing C++ sources on systems where LibTooling does not discover the GCC installation automatically.

Apply from the Aposma repository root, then restart FastAPI.
