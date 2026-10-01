cmake_minimum_required(VERSION 3.20)
project(aposma_analyzer LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(LLVM CONFIG REQUIRED)
find_package(Clang CONFIG REQUIRED)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "LLVM include dirs: ${LLVM_INCLUDE_DIRS}")
message(STATUS "Clang include dirs: ${CLANG_INCLUDE_DIRS}")

include_directories(SYSTEM ${LLVM_INCLUDE_DIRS})
include_directories(SYSTEM ${CLANG_INCLUDE_DIRS})
add_definitions(${LLVM_DEFINITIONS})

add_executable(aposma-analyzer analyzer/src/main.cpp)

target_compile_options(aposma-analyzer PRIVATE -Wall -Wextra -Wpedantic)

target_link_libraries(aposma-analyzer PRIVATE
    clang-cpp
    LLVM
)

install(TARGETS aposma-analyzer RUNTIME DESTINATION bin)
