.PHONY: build test review demo clean

build:
	cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
	cmake --build build --parallel

test:
	pytest

review: build
	python -m codelens.cli review examples/sample_cpp --no-ai

demo: build
	./build/aposma-analyzer examples/sample_cpp/mini.cpp -- -std=c++20 -Iexamples/sample_cpp

clean:
	rm -rf build .pytest_cache .data .venv
