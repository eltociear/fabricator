from datasets import Dataset
from loguru import logger


def preprocess_squad_format(dataset: Dataset) -> Dataset:
    """Preprocesses a dataset in SQuAD format (nested answers) to a dataset in SQuAD format that has flat answers.
    {"answer": {"text": "answer", "start": 0}} -> {"text": "answer"}

    Args:
        dataset (Dataset): A huggingface dataset in SQuAD format.

    Returns:
        Dataset: A huggingface dataset in SQuAD format with flat answers.
    """

    def preprocess(example):
        if example["answers"]:
            example["answers"] = example["answers"].pop()
        else:
            example["answers"] = ""
        return example

    dataset = dataset.flatten().rename_column("answers.text", "answers").map(preprocess)
    return dataset


def postprocess_squad_format(dataset: Dataset, add_answer_start: bool = True) -> Dataset:
    """Postprocesses a dataset in SQuAD format (flat answers) to a dataset in SQuAD format that has nested answers.
    {"text": "answer"} -> {"answer": {"text": "answer", "start": 0}}

    Args:
        dataset (Dataset): A huggingface dataset in SQuAD format.
        add_answer_start (bool, optional): Whether to add the answer start index to the dataset. Defaults to True.

    Returns:
        Dataset: A huggingface dataset in SQuAD format with nested answers.
    """
    if add_answer_start:
        dataset = dataset.map(calculate_answer_start)

    def unify_answers(example):
        example["answers"] = {"text": example["answers"], "start": example["answer_start"]}
        return example

    dataset = dataset.map(unify_answers).remove_columns("answer_start")
    return dataset


def calculate_answer_start(example):
    """Calculates the answer start index for a SQuAD example.

    Args:
        example (Dict): A SQuAD example.

    Returns:
        Dict: The SQuAD example with the answer start index added.
    """
    answer_start = example["context"].find(example["answers"])
    if answer_start < 0:
        logger.info(
            'Could not calculate the answer start because the context "{}" ' 'does not contain the answer "{}".',
            example["context"],
            example["answers"],
        )
        answer_start = -1
    else:
        # check that the answer doesn't occur more than once in the context
        second_answer_start = example["context"].find(example["answers"], answer_start + 1)
        if second_answer_start >= 0:
            logger.info("Could not calculate the answer start because the context contains the answer more than once.")
            answer_start = -1
        else:
            pass
    example["answer_start"] = answer_start
    return example
