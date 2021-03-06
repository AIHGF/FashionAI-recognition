import sys
import pandas as pd
from sklearn.model_selection import train_test_split
import cv2
from tqdm import tqdm
import matplotlib.pyplot as plt
from keras.layers import *
from keras.models import *
from keras.callbacks import *
from keras.optimizers import *
from keras.applications import *
from keras.regularizers import *
from keras.applications.inception_v3 import preprocess_input
# from keras.applications.resnet50 import preprocess_input

import tensorflow as tf
import keras.backend.tensorflow_backend as KTF

config = tf.ConfigProto()
config.gpu_options.per_process_gpu_memory_fraction = 0.8
session = tf.Session(config=config)

DATA = "0408"
WIDTH = 299
TRAIN_DIR = "/home/shuai_shi/Documents/FashionAI-data/train/"
TEST_DIR = "/home/shuai_shi/Documents/FashionAI-data/test/"
RESULT_DIR = "/home/shuai_shi/Documents/FashionAI-data/result/"
MODELS_DIR = "/home/shuai_shi/Documents/FashionAI-data/model/"
CLASSES = ['neck_design_labels', 'collar_design_labels', 'skirt_length_labels', 'pant_length_labels',
           'lapel_design_labels', 'coat_length_labels', 'sleeve_length_labels',
           'neckline_design_labels']



def rotate(image, angle, center=None, scale=1.0):
    (h, w) = image.shape[:2]
    if center is None:
        center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle, scale)
    rotated = cv2.warpAffine(image, M, (w, h))
    return rotated

def con_bright(img, a, g):
    h, w, ch = img.shape
    img2 = np.zeros([h, w, ch], img.dtype)
    return cv2.addWeighted(img, a, img2, 1 - a, g)


df_train = pd.read_csv(TRAIN_DIR + 'label.csv', header=None)
df_train.columns = ['image_id', 'class', 'label']

for iii in range(6, 7):
    cur_class = CLASSES[iii]
    df_load = df_train[(df_train['class'] == cur_class)].copy()
    df_load.reset_index(inplace=True)
    del df_load['index']
    prefix_cls = cur_class.split('_')[0]

    n_class = len(df_load['label'][0])

    cnn_model = InceptionResNetV2(include_top=False, input_shape=(WIDTH, WIDTH, 3), weights='imagenet')
    # resnet50 = ResNet50(include_top=False, input_shape=(WIDTH, WIDTH, 3), weights='imagenet')

    inputs = Input((WIDTH, WIDTH, 3))

    x = inputs
    x = Lambda(preprocess_input, name='preprocessing')(x)
    # x = resnet50(x)
    x = cnn_model(x)
    x = GlobalAveragePooling2D()(x)
    x = Dropout(0.5)(x)
    x = Dense(n_class, activation='softmax', name='softmax')(x)

    model = Model(inputs, x)

    model.load_weights(MODELS_DIR + '{0}.best.h5'.format(prefix_cls))

    adam = Adam(lr=0.001)
    model.compile(optimizer=adam, loss='categorical_crossentropy', metrics=['accuracy'])


    df_test = pd.read_csv(TEST_DIR + 'question.csv', header = None)
    df_test.columns = ['image_id', 'class', 'x']
    del df_test['x']
    df_test.head()

    df_load = df_test[(df_test['class'] == cur_class)].copy()
    df_load.reset_index(inplace=True)
    del df_load['index']

    print('{0}: {1}'.format(cur_class, len(df_load)))
    print(df_load.head())

    n = len(df_load)
    X_test = np.zeros((n, WIDTH, WIDTH, 3), dtype=np.uint8)
    X_test_flip = np.zeros((n, WIDTH, WIDTH, 3), dtype=np.uint8)
    X_test_rotate = np.zeros((n, WIDTH, WIDTH, 3), dtype=np.uint8)
    X_test_con_bright = np.zeros((n, WIDTH, WIDTH, 3), dtype=np.uint8)

    for i in tqdm(range(n)):
        img = cv2.resize(cv2.imread(TEST_DIR + '{0}'.format(df_load['image_id'][i])), (WIDTH, WIDTH))
        X_test[i] = img
        X_test_flip[i] = cv2.flip(img, 1)

        if i % 2 == 0:
            angle = np.random.randint(5, 20)
            a = np.random.randint(12, 16) / 10
            g = np.random.randint(-100, -29)
        else:
            angle = np.random.randint(5, 20) * -1
            a = np.random.randint(5, 9) / 10
            g = np.random.randint(29, 101)

        X_test_rotate[i] = rotate(img, angle)
        X_test_con_bright[i] = con_bright(img, a, g)

    test_np = model.predict(X_test, batch_size = 256)
    test_np_flip = model.predict(X_test_flip, batch_size=256)
    test_np_rotate = model.predict(X_test_rotate, batch_size=256)
    X_test_con_bright = model.predict(X_test_rotate, batch_size=256)

    result = []

    for i, row in df_load.iterrows():
        tmp_list = test_np[i] + test_np_flip[i] + test_np_rotate[i] + X_test_con_bright[i]
        tmp_list /= 4
        tmp_result = ''
        for tmp_ret in tmp_list:
            tmp_result += '{:.4f};'.format(tmp_ret)

        result.append(tmp_result[:-1])

    df_load['result'] = result
    df_load.head()

    df_load.to_csv(RESULT_DIR + ('{}_' + DATA + '.csv').format(prefix_cls), header=None, index=False)

    del(cnn_model)
    del(model)