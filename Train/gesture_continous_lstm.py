# -*- coding: utf-8 -*-

import tensorflow as tf
from tensorflow.contrib import rnn
import matplotlib as plt
import numpy as np

# log_path = '/home/wjyyy/Tensorflow/Log'
# train_path = '/home/wjyyy/Tensorflow/Data/mic_train_5ms.tfrecords'
# val_path = '/home/wjyyy/Tensorflow/Data/mic_test_5ms.tfrecords'
from Utils.ReadAndDecode_Continous import read_and_decode_continous

train_path = '/home/dmrf/GestureNuaaTeam/tensorflow_gesture_data/Gesture_data/abij_train.tfrecords'
val_path = '/home/dmrf/GestureNuaaTeam/tensorflow_gesture_data/Gesture_data/abij_test.tfrecords'

x_train, y_train = read_and_decode_continous(train_path)
x_val, y_val = read_and_decode_continous(val_path)

n_steps = 4400  # time steps
n_inputs = 8
n_classes = 4
n_hidden_units = 512  # neurons in hidden layer
n_layer_num = 1

# 占位符
# RNN 的输入shape = (batch_size, timestep_size, input_size)
x_lstm = tf.placeholder(tf.float32, shape=[None, n_steps * n_inputs], name='input_lstm')  # 4*256 vector
y_label = tf.placeholder(tf.int64, shape=[None, ])
keep_prob = tf.placeholder(tf.float32)

initializer = tf.contrib.layers.xavier_initializer()
weights = {

    'in': tf.Variable(initializer([n_inputs, n_hidden_units])),
    'out': tf.Variable(initializer([n_hidden_units, n_classes]))
    # 'in': tf.Variable(tf.random_normal([n_inputs, n_hidden_units])),
    # 'out': tf.Variable(tf.random_normal([n_hidden_units, n_classes]))
}
biases = {
    'in': tf.Variable(tf.constant(0.1, shape=[n_hidden_units, ])),
    'out': tf.Variable(tf.constant(0.1, shape=[n_classes, ]))
}

batch_size = 1


def RNN(x, weights, biases):
    x = tf.reshape(x, [-1, n_steps, n_inputs])

    lstm_cell = rnn.BasicLSTMCell(num_units=n_hidden_units, forget_bias=1.0, state_is_tuple=True)

    mlstm_cell = rnn.MultiRNNCell([lstm_cell] * n_layer_num, state_is_tuple=True)

    init_state = mlstm_cell.zero_state(batch_size, dtype=tf.float32)

    outputs, final_state = tf.nn.dynamic_rnn(mlstm_cell, inputs=x, initial_state=init_state, time_major=False)
    outputs = tf.unstack(tf.transpose(outputs, [1, 0, 2]))
    results = tf.matmul(outputs[-1], weights['out']) + biases['out']  # 选取最后一个 output

    return results


# Loss
logist = RNN(x_lstm, weights, biases)
logist = tf.nn.softmax(logist, name='softmax_lstm')
prediction_labels = tf.argmax(logist, axis=1, name='output_lstm')

base_lr = 0.5

cross_entropy = tf.losses.sparse_softmax_cross_entropy(labels=y_label, logits=logist)

Optimizer = tf.train.GradientDescentOptimizer(learning_rate=base_lr)
train = Optimizer.minimize(cross_entropy)

correct_prediction = tf.equal(prediction_labels, y_label)
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

# 组合batch
train_batch = batch_size
test_batch = 1

min_after_dequeue_train = train_batch * 2
min_after_dequeue_test = test_batch * 2

num_threads = 3

train_capacity = min_after_dequeue_train + num_threads * train_batch
test_capacity = min_after_dequeue_test + num_threads * test_batch

Training_iterations = 4000
Validation_size = batch_size * 2

test_count = n_classes * 100
Test_iterations = test_count / test_batch

# 使用shuffle_batch可以随机打乱输入
train_x_batch, train_y_batch = tf.train.shuffle_batch([x_train, y_train],
                                                      batch_size=train_batch, capacity=train_capacity,
                                                      min_after_dequeue=min_after_dequeue_train)

# 使用shuffle_batch可以随机打乱输入
test_x_batch, test_y_batch = tf.train.shuffle_batch([x_val, y_val],
                                                    batch_size=test_batch, capacity=test_capacity,
                                                    min_after_dequeue=min_after_dequeue_test)

list_acc = np.zeros(shape=(int(Training_iterations / batch_size) + 1), dtype=np.float32)
list_acc_bat = np.zeros(shape=(int(Training_iterations / batch_size) + 1), dtype=np.int)

list_acc_test = np.zeros(shape=(int(Test_iterations / batch_size) + 1), dtype=np.float32)
list_acc_bat_test = np.zeros(shape=(int(Test_iterations / batch_size) + 1), dtype=np.int)

re_label = np.ndarray(8008, dtype=np.int64)
pr_label = np.ndarray(8008, dtype=np.int64)
error_index = []
# Train
with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    threads = tf.train.start_queue_runners(sess=sess)

    for step in range(Training_iterations + 1):
        train_x, train_y = sess.run([train_x_batch, train_y_batch])
        # 定义一个长度为1024的array
        # x_ndarry_lstm = np.zeros(shape=(batch_size, 1024), dtype=np.float32)

        # tfrecords-->tensor(8,2200,2)-->4*tensor(8,550,2)-->cnn-->4*256-->lstm

        # train_x[0][1][1100][0] is the flag when write tfrecord
        if train_x[0][1][1100][0] == 1 * 6:  # 0.5s-->need train_x[:][1][0:550][0]
            train_x[0][1][1100][0] = 0
            train_x[0][0][1100][0] = 0

        elif train_x[0][1][1100][0] == 2 * 6:  # 1s-->need train_x[:][1][0:1100][0]
            train_x[0][1][1100][0] = 0
            train_x[0][0][1100][0] = 0

        data = np.zeros(shape=(batch_size, 17600), dtype=np.float32)

        train_x = train_x.reshape((-1, 35200))

        a = sess.run(train, feed_dict={x_lstm: train_x, y_label: train_y})

        # Train accuracy
        if step % Validation_size == 0:
            # base_lr = adjust_learning_rate_inv(step, base_lr)
            a = sess.run(accuracy, feed_dict={x_lstm: train_x, y_label: train_y})
            if batch_size == 1:
                if a != 1:
                    error_index.append(train_y[0])
                print('Training Accuracy', step, a, train_y[0]
                      )
            else:
                print('Training Accuracy', step, a
                      )

    l = len(error_index)
    error_numpy = np.zeros((l), dtype=np.int64)
    for i in range(0, l):
        error_numpy[i] = error_index[i]
    np.savetxt('../Data/abij_error_index_onlylstm.txt', error_numpy)

    constant_graph = tf.graph_util.convert_variables_to_constants(sess, sess.graph_def, ["output_lstm"])
    with tf.gfile.FastGFile('../Model/abij_gesture_only_lstm.pb', mode='wb') as f:
        f.write(constant_graph.SerializeToString())
