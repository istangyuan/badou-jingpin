#coding:utf8

import torch
import torch.nn as nn
import numpy as np
import random
import json
import matplotlib.pyplot as plt

"""

基于pytorch的网络编写
实现一个网络完成一个简单nlp任务
判断文本中是否有某些特定字符出现, 特定字符长度为3, 文本长度为6
如果出现,出现了几个,所以一共有4种可能:0,1,2,3

"""

TARGET_CHARS = ['a', 'b', 'c']

class TorchModel(nn.Module):
    def __init__(self, vector_dim, sentence_length, vocab, num_classes: int = 4):
        super(TorchModel, self).__init__()
        self.num_classes = num_classes
        self.embedding = nn.Embedding(len(vocab), vector_dim)  #embedding层
        self.rnn = nn.RNN(num_layers = 1, input_size = vector_dim, hidden_size = vector_dim, batch_first = True)
        # self.pool = nn.AvgPool1d(sentence_length)   #池化层
        self.classify = nn.Linear(vector_dim, 4)     #线性层
        # self.activation = torch.sigmoid     #sigmoid归一化函数
        # self.loss = nn.functional.mse_loss  #loss函数采用均方差损失
        self.loss = nn.functional.cross_entropy

    #当输入真实标签，返回loss值；无真实标签，返回预测值
    def forward(self, x, y=None):
        x = self.embedding(x)                      #(batch_size, sen_len) -> (batch_size, sen_len, vector_dim)
        # x = x.transpose(1, 2)                      # (batch_size, sen_len, vector_dim) -> (batch_size, vector_dim, sen_len)
        x = self.rnn(x)[1]                         #(batch_size, vector_dim, sen_len)->(batch_size, vector_dim, 1)
        x = x.squeeze()                            #(batch_size, vector_dim, 1) -> (batch_size, vector_dim)
        y_pred = self.classify(x)                       #(batch_size, vector_dim) -> (batch_size, 1)
        # y_pred = self.activation(x)                #(batch_size, 1) -> (batch_size, 1)
        if y is not None:
            return self.loss(y_pred, y.squeeze())   #预测值和真实值计算损失
        else:
            return y_pred                 #输出预测结果

#字符集随便挑了一些字，实际上还可以扩充
#为每个字生成一个标号
#{"a":1, "b":2, "c":3...}
#abc -> [1,2,3]
def build_vocab():
    chars = "abcdefghijklmnopqrstuvwxyz"  #字符集
    vocab = {}
    for index, char in enumerate(chars):
        vocab[char] = index   #每个字对应一个序号
    vocab['unk'] = len(vocab)
    return vocab

#随机生成一个样本
#从所有字中选取sentence_length个字
#反之为负样本
def build_sample(target_chars: list, vocab: dict, sentence_length: int):
    #随机从字表选取sentence_length个字，可能重复
    x = [random.choice(list(vocab.keys())) for _ in range(sentence_length)]
    # 判断特殊字符中出现了几个
    # if set(target_chars) & set(x):
    y = len(set(target_chars).intersection(set(x)))
    #指定字都未出现，则为负样本
    # else:
    #     y = 0
    x = [vocab.get(word, vocab['unk']) for word in x]   #将字转换成序号，为了做embedding
    return x, y

#建立数据集
#输入需要的样本数量。需要多少生成多少
def build_dataset(sample_length, vocab, sentence_length, balanced: bool = False):
    dataset_x = []
    dataset_y = []
    counter = {'0': 0, '1': 0, '2': 0, '3': 0}
    i = 0
    label_volume_threshold = sample_length // 4
    while i <= sample_length:
        x, y = build_sample(TARGET_CHARS, vocab, sentence_length)
        if balanced and counter[str(y)] > label_volume_threshold:
            continue
        dataset_x.append(x)
        dataset_y.append([y])
        counter[str(y)] += 1
        i += 1
    print(f"label-0: {counter['0']/sample_length:.2%}\nlabel-1: {counter['1']/sample_length:.2%}\nlabel-2: {counter['2']/sample_length:.2%}\nlabel-3: {counter['3']/sample_length:.2%}")
    return torch.LongTensor(dataset_x), torch.LongTensor(dataset_y)

#建立模型
def build_model(vocab, char_dim, sentence_length):
    model = TorchModel(char_dim, sentence_length, vocab)
    return model

#测试代码
#用来测试每轮模型的准确率
def evaluate(model, vocab, sample_length):
    model.eval()
    x, y = build_dataset(200, vocab, sample_length)   #建立200个用于测试的样本
    print("本次预测集中共有%d个正样本，%d个负样本"%(sum(y), 200 - sum(y)))
    correct, wrong = 0, 0
    with torch.no_grad():
        y_pred = model(x)      #模型预测
        y_pred = torch.argmax(y_pred, dim=1)
        correct = (y.squeeze() == y_pred).sum()
        wrong = y.shape[0] - correct
        # for y_p, y_t in zip(y_pred, y):  #与真实标签进行对比
        #     if float(y_p) < 0.5 and int(y_t) == 0:
        #         correct += 1   #负样本判断正确
        #     elif float(y_p) >= 0.5 and int(y_t) == 1:
        #         correct += 1   #正样本判断正确
        #     else:
        #         wrong += 1
    print("正确预测个数：%d, 正确率：%f"%(correct, correct/(correct+wrong)))
    return correct/(correct+wrong)


def main():
    #配置参数
    epoch_num = 20        #训练轮数
    batch_size = 20       #每次训练样本个数
    train_sample = 500    #每轮训练总共训练的样本总数
    char_dim = 20         #每个字的维度
    sentence_length = 6   #样本文本长度
    learning_rate = 0.005 #学习率
    # 建立字表
    vocab = build_vocab()
    # 建立模型
    model = build_model(vocab, char_dim, sentence_length)
    # 选择优化器
    optim = torch.optim.Adam(model.parameters(), lr=learning_rate)
    log = []
    # 数据
    print("train set label distribution ====")
    x_all, y_all = build_dataset(train_sample, vocab, sentence_length, balanced=True) #构造一组训练样本
    # 训练过程
    for epoch in range(epoch_num):
        model.train()
        watch_loss = []
        for batch in range(int(train_sample / batch_size)):
            x = x_all[batch * batch_size: (batch + 1) * batch_size]
            y = y_all[batch * batch_size: (batch + 1) * batch_size]
            optim.zero_grad()    #梯度归零
            loss = model(x, y)   #计算loss
            loss.backward()      #计算梯度
            optim.step()         #更新权重
            watch_loss.append(loss.item())
        print("=========\n第%d轮平均loss:%f" % (epoch + 1, np.mean(watch_loss)))
        acc = evaluate(model, vocab, sentence_length)   #测试本轮模型结果
        log.append([acc, np.mean(watch_loss)])
    #画图
    plt.plot(range(len(log)), [l[0] for l in log], label="acc")  #画acc曲线
    plt.plot(range(len(log)), [l[1] for l in log], label="loss")  #画loss曲线
    plt.legend()
    plt.show()
    #保存模型
    torch.save(model.state_dict(), "model.pth")
    # 保存词表
    writer = open("vocab.json", "w", encoding="utf8")
    writer.write(json.dumps(vocab, ensure_ascii=False, indent=2))
    writer.close()
    return

#使用训练好的模型做预测
def predict(model_path, vocab_path, input_strings):
    char_dim = 20  # 每个字的维度
    sentence_length = 6  # 样本文本长度
    vocab = json.load(open(vocab_path, "r", encoding="utf8")) #加载字符表
    model = build_model(vocab, char_dim, sentence_length)     #建立模型
    model.load_state_dict(torch.load(model_path))             #加载训练好的权重
    x, y = [], []
    for input_string in input_strings:
        x.append([vocab[char] for char in input_string])  #将输入序列化
        y.append(len(set(TARGET_CHARS).intersection(set(input_string))))
    model.eval()   #测试模式
    with torch.no_grad():  #不计算梯度
        result = model.forward(torch.LongTensor(x))  #模型预测
    for i, input_string in enumerate(input_strings):
        print("输入：%s, 预测类别：%d, 真实类别: %d, 预测分数：%f" % (input_string, int(torch.argmax(result[i])), y[i], float(torch.max(result[i])))) #打印结果



if __name__ == "__main__":
    main()
    test_strings = ["favfee", "wbsdfg", "rqwdbc", "nakbca"]
    predict("model.pth", "vocab.json", test_strings)
