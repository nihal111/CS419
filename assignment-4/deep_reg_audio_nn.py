import tensorflow as tf
import numpy as np
import sys
import csv
import matplotlib.pyplot as plt

# Hyper parameters
HIDDEN_LAYER_NODES_OPTIONS = [300]
DROPOUT_RATE_OPTIONS = [1.0]
LEARNING_RATE = 0.001
BATCH_SIZE = 5000
EPOCHS = 100

# Changed internally, do not change
DROPOUT_RATE = 1.0
HIDDEN_LAYER_NODES = 100

SAVE_PATH = "./checkpoint-reg/save/model.ckpt"
SAVE_FILE = "./predictions-reg/submission.csv"

mins = [0] * 91
ptps = [0] * 91

DEGREE = 1
MULTIPLY_FEATURES = False
INPUT_NODES = 90


def create_graph():
    graph = tf.Graph()
    with graph.as_default():
        # declare the training data placeholders
        # input x - 12 avg + 78 cov = 90
        x = tf.placeholder(tf.float32, [None, INPUT_NODES])
        # now declare the output data placeholder - 9 labels
        y = tf.placeholder(tf.float32, [None, 1])

        # Dropout keep probability
        keep_prob = tf.placeholder(tf.float32)

        # W1 = tf.Variable(tf.random_normal(
        #     [90, HIDDEN_LAYER_NODES], stddev=0.03), name='W1')
        # b1 = tf.Variable(tf.random_normal([HIDDEN_LAYER_NODES]), name='b1')

        # W3 = tf.Variable(tf.random_normal(
        #     [HIDDEN_LAYER_NODES, 1], stddev=0.03), name='W3')
        # b3 = tf.Variable(tf.random_normal([1]), name='b3')

        # W2 = tf.Variable(tf.random_normal(
        #     [HIDDEN_LAYER_NODES, HIDDEN_LAYER_NODES],
        #     stddev=0.03),
        #     name='W2')
        # b2 = tf.Variable(tf.random_normal([HIDDEN_LAYER_NODES]), name='b2')

        # calculate the output of the hidden layer
        hidden_out = tf.contrib.layers.fully_connected(
            x, HIDDEN_LAYER_NODES, activation_fn=tf.nn.relu)
        hidden_out = tf.nn.dropout(hidden_out, keep_prob)

        hidden_out = tf.contrib.layers.fully_connected(
            hidden_out, HIDDEN_LAYER_NODES, activation_fn=tf.nn.relu)
        hidden_out = tf.nn.dropout(hidden_out, keep_prob)

        # calculate the output of the hidden layer
        hidden_out = tf.contrib.layers.fully_connected(
            hidden_out, 1, activation_fn=tf.nn.relu)
        y_ = tf.nn.dropout(hidden_out, keep_prob)

        average_loss = tf.losses.mean_squared_error(y, y_)

        # add an optimiser
        optimiser = tf.train.AdamOptimizer(
            learning_rate=LEARNING_RATE).minimize(average_loss)

        # finally setup the initialisation operator
        init_op = tf.global_variables_initializer()

        # define an accuracy assessment operation
        accuracy = tf.losses.mean_squared_error(y, y_)

    return graph, optimiser, init_op, accuracy, x, y, \
        average_loss, y_, keep_prob


def initialise_plot():
    plt.ion()
    plt.show()
    plt.gcf().clear()
    plt.title('HLN={} LR={} BS={} DR={}'.format(
        HIDDEN_LAYER_NODES, LEARNING_RATE, BATCH_SIZE, DROPOUT_RATE))
    plt.xlabel('Epoch')
    plt.ylabel('MSE')


def plot_graph(train_accuracy, test_accuracy):
    plt.gca().set_color_cycle(['red', 'green'])
    plt.axis([0, len(train_accuracy) +
              1, min(train_accuracy) * 0.9, min(train_accuracy) * 1.5])
    plt.plot(np.arange(1, len(train_accuracy) + 1), np.array(train_accuracy))
    plt.plot(np.arange(1, len(test_accuracy) + 1), np.array(test_accuracy))
    plt.legend(['Train', 'Test'], loc='upper left')
    plt.draw()
    plt.pause(0.0001)


def train(train_examples, train_labels, test_examples,
          test_labels, test_samples, ids):

    results = np.zeros((len(HIDDEN_LAYER_NODES_OPTIONS) *
                        len(DROPOUT_RATE_OPTIONS), 3))
    cnt = 0
    for hln in HIDDEN_LAYER_NODES_OPTIONS:
        for d in DROPOUT_RATE_OPTIONS:
            global HIDDEN_LAYER_NODES, DROPOUT_RATE
            HIDDEN_LAYER_NODES = hln
            DROPOUT_RATE = d
            SAVE_PATH = "./checkpoint-reg/save_{}_{}/model.ckpt".format(
                hln, int(d * 10))
            SAVE_FILE = "./predictions-reg/submission_{}_{}.csv".format(
                hln, int(d * 10))

            graph, optimiser, init_op, accuracy, x, y, \
                average_loss, y_, keep_prob = create_graph()
            session_conf = tf.ConfigProto(
                # device_count={
                #     "GPU":0
                #     }
                gpu_options=tf.GPUOptions(
                    allow_growth=True,
                ),
            )
            with tf.Session(graph=graph, config=session_conf) as sess:
                saver = tf.train.Saver()
                try:
                    saver.restore(sess, SAVE_PATH)
                    print("Model restored.")
                except:
                    # initialise the variables
                    sess.run(init_op)
                    print("Model initialised.")

                total_batch = int(len(train_examples) / BATCH_SIZE)
                train_accuracy = []
                test_accuracy = []
                initialise_plot()
                for epoch in range(EPOCHS):
                    avg_cost = 0
                    for i in range(total_batch):
                        batch_x, batch_y = next_batch(
                            BATCH_SIZE, train_examples, train_labels)
                        ans, _, c = sess.run([y_, optimiser, average_loss],
                                             feed_dict={x: batch_x,
                                                        y: batch_y,
                                                        keep_prob: d})
                        avg_cost += c / total_batch
                        # print("i: {}, avg_cost:{}".format(i, avg_cost))

                    acc = sess.run(accuracy, feed_dict={
                        x: test_examples,
                        y: np.reshape(test_labels, (-1, 1)),
                        keep_prob: 1.0})

                    print("Epoch:{}\tTraining Loss={:.3f}\tTest Loss={:.3f}".format(
                        (epoch + 1), avg_cost, acc))

                    train_accuracy.append(avg_cost)
                    test_accuracy.append(acc)

                    plot_graph(train_accuracy, test_accuracy)

                    # print ans
                    if ((epoch + 1) % 100 == 0):
                        save_path = saver.save(sess, SAVE_PATH)
                        print("Model saved in path: %s" % save_path)

                # store the data
                results[cnt, 0] = acc
                results[cnt, 1] = hln
                results[cnt, 2] = d
                cnt += 1

                save_path = saver.save(sess, SAVE_PATH)
                print("Model saved in path: %s" % save_path)

                plt.savefig('./images-reg/{}_{}_{}_{}.png'.format(hln, d,
                                                                  LEARNING_RATE,
                                                                  BATCH_SIZE),
                            bbox_inches='tight')

                test_prediction = sess.run(
                    y_, feed_dict={x: test_samples, keep_prob: 1.0})

                test_prediction = np.clip(np.reshape(
                    test_prediction, -1), 1922, 2011)

                out = np.asarray([ids, test_prediction])
                np.savetxt(SAVE_FILE, out.transpose(), '%d',
                           delimiter=",", header="ids,label", comments='')

    for result in results:
        print("MSE: {:.3f}\t HIDDEN_LAYER_NODES: {}\t" +
              "DROPOUT: {}").format(result[0], result[1], result[2])


def checkArgs():
    if (len(sys.argv) != 4):
        print "Please enter three arguments. For instance, run: \
        \npython deep_reg_audio_nn.py train_reg.csv dev_reg.csv test-reg.csv"
        exit(0)

    train_file = sys.argv[1]
    dev_file = sys.argv[2]
    test_file = sys.argv[3]

    return train_file, dev_file, test_file


def readCSV(csv_file):
    # open the training file file in universal line ending mode
    # Courtesy: https://stackoverflow.com/a/29082892
    with open(csv_file, 'rU') as infile:
        # read the file as a dictionary for each row ({header : value})
        reader = csv.DictReader(infile)
        parameters = reader.fieldnames
        data = {}
        for row in reader:
            for header, value in row.items():
                try:
                    data[header].append(value)
                except KeyError:
                    data[header] = [value]
    return data, parameters


def next_batch(num, data, labels):
    '''
    Return a total of `num` random samples and labels.
    '''
    idx = np.arange(0, len(data))
    np.random.shuffle(idx)
    idx = idx[:num]
    data_shuffle = [data[i] for i in idx]
    labels_shuffle = np.asarray([labels[i] for i in idx])

    return np.asarray(data_shuffle), np.reshape(labels_shuffle, (-1, 1))


if __name__ == "__main__":
    # Check args
    train_file, dev_file, test_file = checkArgs()

    num_features = 90

    ########################
    # Read training set data
    train_data, parameters = readCSV(train_file)
    train_examples = [[0]] * (len(parameters))
    train_labels = np.array([float(x) for x in train_data[parameters[0]]])
    for i in xrange(1, len(parameters)):
        train_examples[i] = [float(x) for x in train_data[parameters[i]]]
        mins[i], ptps[i] = np.min(train_examples[i]), np.ptp(train_examples[i])
        train_examples[i] = [(float(x) - mins[i]) / ptps[i]
                             for x in train_data[parameters[i]]]

    if (MULTIPLY_FEATURES):
        for a in xrange(1, num_features + 1):
            for b in xrange(a + 1, num_features + 1):
                train_examples.append(np.multiply(
                    train_examples[a], train_examples[b]))

    for a in xrange(1, num_features + 1):
        for d in xrange(2, DEGREE + 1):
            train_examples.append(np.array(train_examples[a]) ** d)

    train_examples = np.array(train_examples[1:]).transpose()
    print("Completed reading training data")

    ###################
    # Read dev set data
    dev_data, parameters = readCSV(dev_file)
    test_examples = [[0]] * (len(parameters))
    test_labels = np.array([float(x) for x in dev_data[parameters[0]]])
    for i in xrange(1, len(parameters)):
        test_examples[i] = [(float(x) - mins[i]) / ptps[i]
                            for x in dev_data[parameters[i]]]

    if (MULTIPLY_FEATURES):
        for a in xrange(1, num_features + 1):
            for b in xrange(a + 1, num_features + 1):
                test_examples.append(np.multiply(
                    test_examples[a], test_examples[b]))

    for a in xrange(1, num_features + 1):
        for d in xrange(2, DEGREE + 1):
            test_examples.append(np.array(test_examples[a]) ** d)

    test_examples = np.array(test_examples[1:]).transpose()
    print("Completed reading dev data")

    ###################
    # Read dev set data
    test_data, parameters = readCSV(test_file)
    test_samples = [[0]] * (len(parameters))
    ids = np.array([float(x) for x in test_data[parameters[0]]]).astype(int)
    for i in xrange(1, len(parameters)):
        test_samples[i] = [(float(x) - mins[i]) / ptps[i]
                           for x in test_data[parameters[i]]]

    if (MULTIPLY_FEATURES):
        for a in xrange(1, num_features + 1):
            for b in xrange(a + 1, num_features + 1):
                test_samples.append(np.multiply(
                    test_samples[a], test_samples[b]))

    for a in xrange(1, num_features + 1):
        for d in xrange(2, DEGREE + 1):
            test_samples.append(np.array(test_samples[a]) ** d)

    INPUT_NODES = len(test_samples) - 1

    test_samples = np.array(test_samples[1:]).transpose()
    print("Completed reading test data")

    train(train_examples, train_labels, test_examples,
          test_labels, test_samples, ids)
