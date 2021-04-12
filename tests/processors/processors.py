from datagrowth.processors import Processor


class ProcessorMock(Processor):

    ARGS_NORMAL_METHODS = ["normal_method"]
    ARGS_BATCH_METHODS = ["batch_method"]

    def normal_method(self):
        pass

    def batch_method(self):
        pass

    def default_method(self):
        pass
