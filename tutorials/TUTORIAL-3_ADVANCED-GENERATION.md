# Tutorial 2: Generate advanced datasets

## Infer prompt from dataset

Huggingface Dataset objects provide the possibility to infer a prompt from the dataset. This can be achieved by using
the `infer_prompt_from_dataset` function from the `ai_dataset_generator.prompts` module. This function takes a dataset
as input and returns a `BasePrompt` object. The `BasePrompt` object contains the task description, the label options
and the respective columns which can be used to generate a dataset with the `DatasetGenerator` class. The default 
assignment is that data is going to be generated for the label column specified in the `task_template`.

```python
from datasets import load_dataset
from ai_dataset_generator.prompts import infer_prompt_from_dataset

dataset = load_dataset("imdb", split="train")
prompt = infer_prompt_from_dataset(dataset)

print(prompt.get_prompt_text() + "\n---")

label_options = dataset.features["label"].names
fewshot_example = dataset.shuffle(seed=42).select([0])

print(prompt.get_prompt_text(label_options, fewshot_example))
```

The output of this script is:

```text
Classify the following texts exactly into one of the following categories: {}.

text: {text}
label: 
---
Classify the following texts exactly into one of the following categories: neg, pos.

text: There is no relation at all between Fortier and Profiler but the fact that both are police series [...]
label: 1

text: {text}
label: 
```

This feature is particularly useful, if you have nested structures that follow a common format such as for
extractive question answering:

```python
from datasets import load_dataset
from ai_dataset_generator.prompts import infer_prompt_from_dataset

dataset = load_dataset("imdb", split="train")
prompt = infer_prompt_from_dataset(dataset)

print(prompt.get_prompt_text() + "\n---")

label_options = dataset.features["label"].names
fewshot_example = dataset.shuffle(seed=42).select([0])

print(prompt.get_prompt_text(label_options, fewshot_example))
```

This script outputs:

```text
Given a context and a question, generate an answer that occurs exactly and only once in the text.

context: {context}
question: {question}
answers: 
---
Given a context and a question, generate an answer that occurs exactly and only once in the text.

context: The Roman Catholic Church canon law also includes the main five rites (groups) of churches which are in full union with the Roman Catholic Church and the Supreme Pontiff:
question: What term characterizes the intersection of the rites with the Roman Catholic Church?
answers: {'text': ['full union'], 'answer_start': [104]}

context: {context}
question: {question}
answers: 
```

## Preprocess datasets

The previous example emphasized how easy prompts can be generated using huggingface Datasets. However,
there is a potential mismatch between label names and label IDs in the fewshot data points
or structured answers as for the example of SQuAD. In order to best utilize the LLM, datasets will often
require some sort of preprocessing.

```text
Classify the following texts exactly into one of the following categories: **neg, pos**.

text: There is no relation at all between Fortier and Profiler but the fact that both are police series [...]
**label: 1**

---

Given a context and a question, generate an answer that occurs exactly and only once in the text.

context: The Roman Catholic Church canon law also includes the main five rites (groups) of churches which are in full union with the Roman Catholic Church and the Supreme Pontiff:
question: What term characterizes the intersection of the rites with the Roman Catholic Church?
answers: **{'text': ['full union'], 'answer_start': [104]}**
```

To do so, we provide a range of preprocessing functions for downstream tasks.

### Text Classification

The `convert_label_ids_to_texts` function transform your text classification dataset with label IDs into textual
labels. The default will be the label names specified in the features column. You can also directly return the label
options if you want to create a custom prompt from `BasePrompt` class. In the example, we only
return them for logging since we use our `infer_prompt_from_dataset` method which automatically
uses the label names specified in the dataset.

```python
from datasets import load_dataset
from ai_dataset_generator.prompts import infer_prompt_from_dataset
from ai_dataset_generator.dataset_transformations.text_classification import convert_label_ids_to_texts

dataset = load_dataset("imdb", split="train")
prompt = infer_prompt_from_dataset(dataset)
dataset, label_options = convert_label_ids_to_texts(
    dataset=dataset, 
    label_column="label",
    return_label_options=True
)

fewshot_example = dataset.shuffle(seed=42).select([0])
print(prompt.get_prompt_text(label_options, fewshot_example))
```

Which yields:

```text
Classify the following texts exactly into one of the following categories: neg, pos.

text: There is no relation at all between Fortier and Profiler but the fact that both are police series [...]
label: pos

text: {text}
label: 
```

If we want to provide more meaningful names we can do so by specifying `expanded_label_mapping`.
Remember to update the label options accordingly in the `BasePrompt` class.

```python
extended_mapping = {0: "negative", 1: "positive"}
dataset, label_options = convert_label_ids_to_texts(
    dataset=dataset,
    label_column="label",
    expanded_label_mapping=extended_mapping,
    return_label_options=True
)
prompt.label_options = label_options
```

This yields:

```text
Classify the following texts exactly into one of the following categories: positive, negative.

text: There is no relation at all between Fortier and Profiler but the fact that both are police series [...]
label: positive

text: {text}
label: 
```

During the dataset generation we expect the model to generate the labels in the explicitly defined label options but
do not filter if this is not the case. We observed in our experiments that this does not occur if the prompt is precise
and consistent. Once the dataset is generated, one can easily convert the string labels back to label IDs by
using huggingface's `class_encode_labels` function.

```python
dataset = dataset.class_encode_column("label")
print("Labels: " + str(dataset["label"][:5]))
print("Features: " + str(dataset.features["label"]))
```

Which yields:

```text
Labels: [0, 0, 0, 0, 0]
Features: ClassLabel(names=['negative', 'positive'], id=None)
```

### Question Answering (Extractive)

For question answering, we provide two functions to preprocess and postprocess the dataset. The preprocessing function
will convert datasets in SQuAD-format to a flat format such that the inputs to the LLM will be strings.
The postprocessing function will convert the predictions back to the SQuAD-format by calculating the answer 
start and log if this answer can't be found in the context or if the answer occurs multiple times.

```python
from datasets import load_dataset
from ai_dataset_generator.prompts import infer_prompt_from_dataset
from ai_dataset_generator.dataset_transformations.question_answering import preprocess_squad_format, \
    postprocess_squad_format

dataset = load_dataset("squad_v2", split="train")
prompt = infer_prompt_from_dataset(dataset)

dataset = preprocess_squad_format(dataset)

print(prompt.get_prompt_text(None, dataset.select([0])) + "\n---")

dataset = postprocess_squad_format(dataset)
print(dataset[0]["answers"])
```

Which yields:

```text
Given a context and a question, generate an answer that occurs exactly and only once in the text.

context: Beyoncé Giselle Knowles-Carter (/biːˈjɒnseɪ/ bee-YON-say) (born September 4, 1981) is an American singer, songwriter, record producer and actress. Born and raised in Houston, Texas, she performed in various singing and dancing competitions as a child, and rose to fame in the late 1990s as lead singer of R&B girl-group Destiny's Child. Managed by her father, Mathew Knowles, the group became one of the world's best-selling girl groups of all time. Their hiatus saw the release of Beyoncé's debut album, Dangerously in Love (2003), which established her as a solo artist worldwide, earned five Grammy Awards and featured the Billboard Hot 100 number-one singles "Crazy in Love" and "Baby Boy".
question: When did Beyonce start becoming popular?
answers: in the late 1990s

context: {context}
question: {question}
answers: 
---
{'start': 269, 'text': 'in the late 1990s'}
```

### Named Entity Recognition

If you want to generate a dataset for named entity recognition without any preprocesing, the prompt would be difficult
to understand for the LLM.

```python
from datasets import load_dataset
from ai_dataset_generator.prompts import BasePrompt

dataset = load_dataset("conll2003", split="train")
prompt = BasePrompt(
    task_description="Annotate each token with its named entity label: {}.",
    generate_data_for_column="ner_tags",
    fewshot_example_columns=["tokens"],
    label_options=dataset.features["ner_tags"].feature.names,
)

print(prompt.get_prompt_text(prompt.label_options, dataset.select([0])))
```

Which outputs:

```text
Annotate each token with its named entity label: O, B-PER, I-PER, B-ORG, I-ORG, B-LOC, I-LOC, B-MISC, I-MISC.

tokens: ['EU', 'rejects', 'German', 'call', 'to', 'boycott', 'British', 'lamb', '.']
ner_tags: [3, 0, 7, 0, 0, 0, 7, 0, 0]

tokens: {tokens}
ner_tags: 
```

To make the prompt more understandable, we can preprocess the dataset such that the labels are converted to spans.
This can be done by using the `convert_token_labels_to_spans` function. The function will also return the label options

```python
from datasets import load_dataset
from ai_dataset_generator.prompts import BasePrompt
from ai_dataset_generator.dataset_transformations.token_classification import convert_token_labels_to_spans

dataset = load_dataset("conll2003", split="train")
dataset, label_options = convert_token_labels_to_spans(dataset, "tokens", "ner_tags")
prompt = BasePrompt(
    task_description="Annotate each token with its named entity label: {}.",
    generate_data_for_column="ner_tags",
    fewshot_example_columns=["tokens"],
    label_options=label_options,
)

print(prompt.get_prompt_text(prompt.label_options, dataset.select([0])))
```
Output:
```text
Annotate each token with its named entity label: MISC, ORG, PER, LOC.

tokens: EU rejects German call to boycott British lamb . 
ner_tags: ORG -> EU
MISC -> German, British

tokens: {tokens}
ner_tags: 
```

As in text classification, we can also specfiy more semantically precise labels with the `expanded_label_mapping`:

```python
expanded_label_mapping = {
    0: "O",
    1: "B-person",
    2: "I-person",
    3: "B-location",
    4: "I-location",
    5: "B-organization",
    6: "I-organization",
    7: "B-miscellaneous",
    8: "I-miscellaneous",
}

dataset, label_options = convert_token_labels_to_spans(
    dataset=dataset,
    token_column="tokens",
    label_column="ner_tags",
    expanded_label_mapping=expanded_label_mapping
)
```

Output:

```text
Annotate each token with its named entity label: organization, person, location, miscellaneous.

tokens: EU rejects German call to boycott British lamb . 
ner_tags: location -> EU
miscellaneous -> German, British

tokens: {tokens}
ner_tags: 
```

Once the dataset is created, we can use the `convert_spans_to_token_labels` function to convert spans back to labels 
IDs. This function will only add spans the occur only once in the text. If a span occurs multiple times, it will be
ignored. Note: this takes rather long is currently build on spacy. We are working on a faster implementation or welcome
contributions.

```python
from ai_dataset_generator.dataset_transformations.token_classification import convert_spans_to_token_labels
dataset = convert_spans_to_token_labels(
    dataset=dataset.select(range(20)),
    token_column="tokens",
    label_column="ner_tags",
    id2label=expanded_label_mapping
)
```

Outputs:

```Text
{'id': '1', 'tokens': ['Peter', 'Blackburn'], 'pos_tags': [22, 22], 'chunk_tags': [11, 12], 'ner_tags': [1, 2]}
```

## Adapt to arbitrary datasets

The `BasePrompt` class is designed to be easily adaptable to arbitrary datasets. Just like in the examples for text 
classification, token classification or question answering, you can specify the task description, the column to generate
data for and the fewshot example columns. The only difference is that you have to specify the optional label options 
yourself.

### Translation
```python
import os
from datasets import Dataset
from haystack.nodes import PromptNode
from ai_dataset_generator import DatasetGenerator
from ai_dataset_generator.prompts import BasePrompt

fewshot_dataset = Dataset.from_dict({
    "german": ["Der Film ist großartig!", "Der Film ist schlecht!"],
    "english": ["This movie is great!", "This movie is bad!"],
})

unlabeled_dataset = Dataset.from_dict({
    "english": ["This movie was a blast!", "This movie was not bad!"],
})

prompt = BasePrompt(
    task_description="Translate to german:", # Since we do not have a label column, 
    # we can just specify the task description
    generate_data_for_column="german",
    fewshot_example_columns="english",
)

prompt_node = PromptNode(
    model_name_or_path="gpt-3.5-turbo",
    api_key=os.environ.get("OPENAI_API_KEY"),
    max_length=100,
)

generator = DatasetGenerator(prompt_node)
generated_dataset = generator.generate(
    prompt_template=prompt,
    fewshot_dataset=fewshot_dataset,
    fewshot_examples_per_class=2, # Take both fewshot examples per prompt
    fewshot_label_sampling_strategy=None, # Since we do not have a class label column, we can just set this to None 
    # (default)
    unlabeled_dataset=unlabeled_dataset,
    max_prompt_calls=2,
)

generated_dataset.push_to_hub("your-first-generated-dataset")
```

### Textual similarity
```python
import os
from datasets import load_dataset
from haystack.nodes import PromptNode
from ai_dataset_generator import DatasetGenerator
from ai_dataset_generator.prompts import BasePrompt
from ai_dataset_generator.dataset_transformations.text_classification import convert_label_ids_to_texts

dataset = load_dataset("glue", "mrpc", split="train")
dataset, label_options = convert_label_ids_to_texts(dataset, "label", return_label_options=True) # convert the
# label ids to text labels and return the label options

fewshot_dataset = dataset.select(range(10))
unlabeled_dataset = dataset.select(range(10, 20))

prompt = BasePrompt(
    task_description="Annotate the sentence pair whether it is: {}",
    label_options=label_options,
    generate_data_for_column="label",
    fewshot_example_columns=["sentence1", "sentence2"], # we can pass an array of columns to use for the fewshot
)

prompt_node = PromptNode(
    model_name_or_path="gpt-3.5-turbo",
    api_key=os.environ.get("OPENAI_API_KEY"),
    max_length=100,
)

generator = DatasetGenerator(prompt_node)
generated_dataset, original_dataset = generator.generate(
    prompt_template=prompt,
    fewshot_dataset=fewshot_dataset,
    fewshot_examples_per_class=1, # Take 1 fewshot examples per class per prompt
    fewshot_sampling_column="label", # We want to sample fewshot examples based on the label column
    fewshot_label_sampling_strategy="stratified", # We want to sample fewshot examples stratified by class
    unlabeled_dataset=unlabeled_dataset,
    max_prompt_calls=2,
    return_unlabeled_dataset=True, # We can return the original unlabelled dataset which might be interesting in this
    # case to compare the annotation quality
)

generated_dataset = generated_dataset.class_encode_column("label")

generated_dataset.push_to_hub("your-first-generated-dataset")
```

You can also easily switch out columns to be annotated if you want, for example, to generate a second sentence given a
first sentence and a label like:

```python
import os
from datasets import load_dataset
from haystack.nodes import PromptNode
from ai_dataset_generator import DatasetGenerator
from ai_dataset_generator.prompts import BasePrompt
from ai_dataset_generator.dataset_transformations.text_classification import convert_label_ids_to_texts

dataset = load_dataset("glue", "mrpc", split="train")
dataset, label_options = convert_label_ids_to_texts(dataset, "label", return_label_options=True) # convert the
# label ids to text labels and return the label options

fewshot_dataset = dataset.select(range(10))
unlabeled_dataset = dataset.select(range(10, 20))

prompt = BasePrompt(
    task_description="Generate a sentence that is {} to sentence1.",
    label_options=label_options,
    generate_data_for_column="sentence2",
    fewshot_example_columns=["sentence1", "label"], # we can pass an array of columns to use for the fewshot
)

prompt_node = PromptNode(
    model_name_or_path="gpt-3.5-turbo",
    api_key=os.environ.get("OPENAI_API_KEY"),
    max_length=100,
)

generator = DatasetGenerator(prompt_node)
generated_dataset, original_dataset = generator.generate(
    prompt_template=prompt,
    fewshot_dataset=fewshot_dataset,
    fewshot_examples_per_class=1, # Take 1 fewshot examples per class per prompt
    fewshot_sampling_column="label", # We want to sample fewshot examples based on the label column
    fewshot_label_sampling_strategy="stratified", # We want to sample fewshot examples stratified by class
    unlabeled_dataset=unlabeled_dataset,
    max_prompt_calls=2,
    return_unlabeled_dataset=True, # We can return the original unlabelled dataset which might be interesting in this
    # case to compare the annotation quality
)

generated_dataset = generated_dataset.class_encode_column("label")

generated_dataset.push_to_hub("your-first-generated-dataset")
```

### Token classification
Note: Token classification is currently still in development and often yields instable results. In particular the 
conversion between spans and token labels welcomes contributions for a more stable implementation.

```python
import os
from datasets import load_dataset
from haystack.nodes import PromptNode
from ai_dataset_generator import DatasetGenerator
from ai_dataset_generator.prompts import BasePrompt
from ai_dataset_generator.dataset_transformations.token_classification import convert_token_labels_to_spans,\
    convert_spans_to_token_labels

dataset = load_dataset("conll2003", split="train")
expanded_label_mapping = {
    0: "O",
    1: "B-person",
    2: "I-person",
    3: "B-location",
    4: "I-location",
    5: "B-organization",
    6: "I-organization",
    7: "B-miscellaneous",
    8: "I-miscellaneous",
}
dataset, label_options = convert_token_labels_to_spans(dataset, "tokens", "ner_tags", expanded_label_mapping)

fewshot_dataset = dataset.select(range(10))
unlabeled_dataset = dataset.select(range(10, 20))

prompt = BasePrompt(
    task_description="Annotate each token with its named entity label: {}.",
    generate_data_for_column="ner_tags",
    fewshot_example_columns="tokens",
    label_options=list(expanded_label_mapping.values()),
)

prompt_node = PromptNode(
    model_name_or_path="gpt-3.5-turbo",
    api_key=os.environ.get("OPENAI_API_KEY"),
    max_length=100,
)

generator = DatasetGenerator(prompt_node)
generated_dataset, original_dataset = generator.generate(
    prompt_template=prompt,
    fewshot_dataset=fewshot_dataset,
    fewshot_examples_per_class=3, # Take 3 fewshot examples (for token-level class we do not sample per class)
    unlabeled_dataset=unlabeled_dataset,
    max_prompt_calls=10,
    return_unlabeled_dataset=True,
)

generated_dataset = convert_spans_to_token_labels(
    dataset=generated_dataset,
    token_column="tokens",
    label_column="ner_tags",
    id2label=expanded_label_mapping
)

original_dataset = convert_spans_to_token_labels(
    dataset=original_dataset,
    token_column="tokens",
    label_column="ner_tags",
    id2label=expanded_label_mapping
)
```