import tensorflow as tf

from models.api_encoder import ApiEncoder
from models.cnn_encoder import CNNEncoder
from models.bert_encoder import BertEncoder
from utils.metrics import cos_loss, mrr

class Model:

    def __init__(self, params, sc_vocab):
        self.params = params
        self.sc_vocab = sc_vocab
        self.desc_encoder = self._create_desc_encoder()
        self.sc_encoder = self._create_sc_encoder()
        self.model = self._make_graph()
        self._compile_models()
        

    def _create_desc_encoder(self):
        scope = "desc"
        return BertEncoder(scope=scope,
                           max_seq_length=self.params.desc_max_seq_len,
                           num_layers=self.params.desc_bert_layers,
                           hidden_size=self.params.desc_bert_hidden_size,
                           att_heads=self.params.desc_bert_heads,
                           hidden_dropout=self.params.sc_dropout_rate,
                           output_units=self.params.output_units)
    
    def _create_sc_encoder(self):
        scope = "sc"
        new_model = None
        sc_vocab_size = len(self.sc_vocab.token_to_id)
        if self.params.model == "n-gram":
            
            conv_kernel_sizes = []
            for key, value in self.params._get_kwargs():
                if key == "sc-add-conv" and value is not None:
                    conv_kernel_sizes.append(value)
            
            new_model = CNNEncoder(scope=scope, 
                                   max_seq_length=self.params.sc_max_tok_len,
                                   vocab_size=sc_vocab_size,
                                   emb_size=self.params.emb_size,
                                   conv_kernel_sizes=conv_kernel_sizes,
                                   conv_n_filters=self.params.sc_conv_n_filters,
                                   dropout_rate=self.params.sc_dropout_rate,
                                   output_units=self.params.output_units)
        elif self.params.model == "api":
            new_model = ApiEncoder(scope=scope,
                                   max_fname_length=self.params.sc_max_fname_len,
                                   max_api_length=self.params.sc_max_api_len,
                                   max_tok_length=self.params.sc_max_tok_len,
                                   vocab_size=sc_vocab_size,
                                   emb_size=self.params.emb_size,
                                   dropout_rate=self.params.sc_dropout_rate,
                                   lstm_units=self.params.sc_rnn_units,
                                   lstm_rec_dropout_rate=self.params.sc_rnn_dropout_rate,
                                   output_units=self.params.output_units)
        elif self.params.model == "bert":
            new_model = BertEncoder(scope=scope,
                                    max_seq_length=self.params.sc_max_tok_len,
                                    num_layers=self.params.sc_bert_layers,
                                    hidden_size=self.params.sc_bert_hidden_size,
                                    att_heads=self.params.sc_bert_heads,
                                    hidden_dropout=self.params.sc_dropout_rate,
                                    output_units=self.params.output_units)
        return new_model

    def _make_graph(self):
        eps = 1e-10
        norm_desc = tf.norm(self.desc_encoder.outputs, axis=-1, keepdims=True) + eps
        norm_sc   = tf.norm(self.sc_encoder.outputs, axis=-1, keepdims=True)   + eps
        self.outputs = tf.matmul(self.desc_encoder.outputs/norm_desc,
                                 self.sc_encoder.outputs/norm_sc,
                                 transpose_a=False,
                                 transpose_b=True,
                                 name='desc_sc_cos_sim_logits')  # (batch_size, batch_size)
        self.inputs = [*self.desc_encoder.inputs, *self.sc_encoder.inputs]
        reqver_model = tf.keras.Model(inputs=self.inputs,
                                      outputs=self.outputs,
                                      name=f'reqver_{self.params.model}_model')
        
        return reqver_model

    def _compile_models(self):
        self.model.compile(loss=cos_loss, optimizer=self.params.optimizer, metrics=[mrr])
        self.desc_encoder.model.compile(loss=cos_loss, optimizer=self.params.optimizer)
        self.sc_encoder.model.compile(loss=cos_loss, optimizer=self.params.optimizer)

    def train(self):
        pass

    def evaluate(self):
        pass
