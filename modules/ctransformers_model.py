from ctransformers import AutoConfig, AutoModelForCausalLM

from modules import shared
from modules.callbacks import Iteratorize
from modules.logging_colors import logger


class CtransformersModel:
    def __init__(self):
        pass

    @classmethod
    def from_pretrained(self, path):
        result = self()

        # ctransformers uses -1 for random seed
        config = AutoConfig.from_pretrained(
            str(path),
            threads=shared.args.threads,
            gpu_layers=shared.args.n_gpu_layers,
            batch_size=shared.args.n_batch,
            stream=True,
            seed=(-1 if shared.args.llama_cpp_seed == 0 else shared.args.llama_cpp_seed)
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            str(result.model_dir(path) if result.model_type_is_auto() else path),
            model_type=(None if result.model_type_is_auto() else shared.args.model_type),
            config=config
        )

        logger.info(f'Using ctransformers model_type: {self.model.model_type} for {self.model.model_path}')
        return result, result

    def model_type_is_auto(self):
        return shared.args.model_type == "Auto" or shared.args.model_type == "None"

    def model_dir(self, path):
        if path.is_file():
            return path.parent

        return path

    def encode(self, string, **kwargs):
        return self.model.tokenize(string)

    def decode(self, ids):
        return self.model.detokenize(ids)

    def generate(self, prompt, state, callback=None):
        prompt = prompt if type(prompt) is str else prompt.decode()
        generator = self.model._stream(
            prompt=prompt,
            max_new_tokens=state['max_new_tokens'],
            temperature=state['temperature'],
            top_p=state['top_p'],
            top_k=state['top_k'],
            repetition_penalty=state['repetition_penalty'],
            last_n_tokens=state['repetition_penalty_range'],
            threads=shared.args.threads
        )

        output = ""
        for token in generator:
            if callback:
                callback(token)

            output += token

        return output

    def generate_with_streaming(self, *args, **kwargs):
        with Iteratorize(self.generate, args, kwargs, callback=None) as generator:
            reply = ''
            for token in generator:
                reply += token
                yield reply
