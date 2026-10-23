# Research Plan

## Question

Does structured program context improve an existing local SLM's software-maintenance outputs?

## Baselines

1. Raw code → SLM
2. Code + Git diff → SLM
3. Code + diff + AST facts → SLM
4. Code + diff + AST + static findings → SLM
5. Full evidence package → SLM

## Metrics

### Review

- precision
- recall
- F1
- false-positive rate
- severity agreement
- evidence grounding

### Documentation

- factual accuracy
- completeness
- consistency
- hallucination rate
- stale-document detection accuracy

### Systems

- latency
- memory usage
- prompt size
- model generation time

## Experimental discipline

Change one major context variable at a time. Keep the model, temperature, dataset, and evaluation rubric fixed where possible.
