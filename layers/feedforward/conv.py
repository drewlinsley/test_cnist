import numpy as np
import tensorflow as tf
from layers.feedforward import normalization
from layers.feedforward import pooling


def input_layer(
        X,
        reuse,
        training,
        features,
        conv_kernel_size,
        pool_kernel_size=False,
        pool_kernel_strides=False,
        name='l0',
        conv_strides=(1, 1),
        conv_padding='same',
        conv_activation=tf.nn.relu,
        var_scope='input_1',
        pool=False,
        pool_type='max'):
    """Input layer for recurrent experiments in Kim et al., 2019."""
    if not pool_kernel_size or not pool_kernel_strides:
        pool = False
    with tf.variable_scope(var_scope, reuse=reuse):
        in_emb = tf.layers.conv2d(
            inputs=X,
            filters=features,
            kernel_size=conv_kernel_size,
            name='conv_0_%s' % name,
            strides=conv_strides,
            padding=conv_padding,
            activation=conv_activation,
            trainable=training,
            use_bias=True)
        if pool:
            if pool_type == 'max':
                in_emb = pooling.max_pool(
                    bottom=in_emb,
                    name='pool_%s' % name,
                    k=pool_kernel_size,
                    s=pool_kernel_strides)
            else:
                raise NotImplementedError
        in_emb = tf.layers.conv2d(
            inputs=in_emb,
            filters=features,
            kernel_size=conv_kernel_size,
            name='conv_1_%s' % name,
            strides=conv_strides,
            padding=conv_padding,
            activation=conv_activation,
            trainable=training,
            use_bias=True)
    return in_emb


def skinny_input_layer(
        X,
        reuse,
        training,
        features,
        conv_kernel_size,
        pool_kernel_size=False,
        pool_kernel_strides=False,
        name='l0',
        conv_strides=(1, 1),
        conv_padding='same',
        conv_activation=tf.nn.relu,
        var_scope='input_1',
        pool=False,
        pool_type='max'):
    """Input layer for recurrent experiments in Kim et al., 2019."""
    if not pool_kernel_size or not pool_kernel_strides:
        pool = False
    with tf.variable_scope(var_scope, reuse=reuse):
        in_emb = tf.layers.conv2d(
            inputs=X,
            filters=features,
            kernel_size=conv_kernel_size,
            name='conv_0_%s' % name,
            strides=conv_strides,
            padding=conv_padding,
            activation=conv_activation,
            trainable=training,
            use_bias=True)
        if pool:
            if pool_type == 'max':
                in_emb = pooling.max_pool(
                    bottom=in_emb,
                    name='pool_%s' % name,
                    k=pool_kernel_size,
                    s=pool_kernel_strides)
            else:
                raise NotImplementedError
    return in_emb


def readout_layer(
        activity,
        reuse,
        training,
        output_shape,
        var_scope='readout_1',
        pool_type='max',
        renorm=True,
        features=2):
    """Readout layer for recurrent experiments in Kim et al., 2019."""
    with tf.variable_scope(var_scope, reuse=reuse):
        activity = conv_layer(
            bottom=activity,
            name='pre_readout_conv',
            num_filters=features,
            kernel_size=1,
            trainable=training,
            use_bias=False)
        pool_aux = {'pool_type': pool_type}
        activity = pooling.global_pool(
            bottom=activity,
            name='pre_readout_pool',
            aux=pool_aux)
        activity = normalization.batch(
            bottom=activity,
            renorm=True,
            name='readout_1_bn',
            training=training)

    with tf.variable_scope('readout_2', reuse=reuse):
        activity = tf.layers.flatten(
            activity,
            name='flat_readout')
        activity = tf.layers.dense(
            inputs=activity,
            units=output_shape)
    return activity


def conv_layer(
        bottom,
        name,
        num_filters=None,
        kernel_size=None,
        stride=[1, 1, 1, 1],
        padding='SAME',
        trainable=True,
        use_bias=True,
        reuse=False,
        data_format='NHWC',
        aux={}):
    """2D convolutional layer with pretrained weights."""
    if data_format == 'NHWC':
        chd = -1
    elif data_format == 'NCHW':
        chd = 1
    else:
        raise NotImplementedError(data_format)
    in_ch = int(bottom.get_shape()[chd])
    if 'transpose_inds' in aux.keys():
        transpose_inds = aux['transpose_inds']
    else:
        transpose_inds = False
    if 'pretrained' in aux.keys():
        kernel_initializer = np.load(aux['pretrained']).item()
        key = aux['pretrained_key']
        if key == 'weights':
            key = kernel_initializer.keys()[0]
        kernel_initializer, preloaded_bias = kernel_initializer[key]
        if not len(preloaded_bias) and use_bias:
            if data_format == 'NHWC':
                bias_shape = [1, 1, 1, kernel_initializer.shape[-1]]
            elif data_format == 'NCHW':
                bias_shape = [1, kernel_initializer.shape[-1], 1, 1]
            else:
                raise NotImplementedError(data_format)
            bias = tf.get_variable(
                name='%s_conv_bias' % name,
                initializer=tf.zeros_initializer(),
                shape=bias_shape,
                trainable=trainable)
        if transpose_inds:
            kernel_initializer = kernel_initializer.transpose(transpose_inds)
        kernel_size = kernel_initializer.shape[0]
        pretrained = True
    else:
        assert num_filters is not None, 'Describe your filters'
        assert kernel_size is not None, 'Describe your kernel_size'
        if 'initializer' in aux.keys():
            kernel_initializer = aux['initializer']
        else:
            # kernel_initializer = tf.variance_scaling_initializer()
            kernel_spec = [kernel_size, kernel_size, in_ch, num_filters]
            kernel_initializer = [
                kernel_spec,
                tf.contrib.layers.xavier_initializer(uniform=False)]
        pretrained = False
    if pretrained:
        filters = tf.get_variable(
            name='%s_pretrained' % name,
            initializer=kernel_initializer,
            trainable=trainable)
    else:
        filters = tf.get_variable(
            name='%s_initialized' % name,
            shape=kernel_initializer[0],
            initializer=kernel_initializer[1],
            trainable=trainable)
        if use_bias:
            if data_format == 'NHWC':
                bias_shape = tf.zeros([1, 1, 1, num_filters])
            elif data_format == 'NCHW':
                bias_shape = tf.zeros([1, num_filters, 1, 1])
            else:
                raise NotImplementedError(data_format)
            bias = tf.get_variable(
                name='%s_bias' % name,
                initializer=bias_shape,
                trainable=trainable)
    activity = tf.nn.conv2d(
        bottom,
        filters,
        strides=stride,
        padding='SAME',
        data_format=data_format)
    if use_bias:
        activity += bias
    if 'nonlinearity' in aux.keys():
        if aux['nonlinearity'] == 'square':
            activity = tf.pow(activity, 2)
        elif aux['nonlinearity'] == 'relu':
            activity = tf.nn.relu(activity)
        else:
            raise NotImplementedError(aux['nonlinearity'])
    return activity


def down_block(
        layer_name,
        bottom,
        reuse,
        kernel_size,
        num_filters,
        training,
        stride=(1, 1),
        padding='same',
        data_format='channels_last',
        renorm=False,
        use_bias=False,
        include_pool=True):
    """Forward block for seung model."""
    with tf.variable_scope('%s_block' % layer_name, reuse=reuse):
        with tf.variable_scope('%s_layer_1' % layer_name, reuse=reuse):
            x = tf.layers.conv2d(
                inputs=bottom,
                filters=num_filters,
                kernel_size=kernel_size[0],
                name='%s_1' % layer_name,
                strides=stride,
                padding=padding,
                data_format=data_format,
                trainable=training,
                use_bias=use_bias)
            x = normalization.batch(
                bottom=x,
                name='%s_bn_1' % layer_name,
                data_format=data_format,
                renorm=renorm,
                training=training)
            x = tf.nn.elu(x)
            skip = tf.identity(x)

        with tf.variable_scope('%s_layer_2' % layer_name, reuse=reuse):
            x = tf.layers.conv2d(
                inputs=x,
                filters=num_filters,
                kernel_size=kernel_size[1],
                name='%s_2' % layer_name,
                strides=stride,
                padding=padding,
                data_format=data_format,
                trainable=training,
                use_bias=use_bias)
            x = normalization.batch(
                bottom=x,
                name='%s_bn_2' % layer_name,
                data_format=data_format,
                renorm=renorm,
                training=training)
            x = tf.nn.elu(x)

        with tf.variable_scope('%s_layer_3' % layer_name, reuse=reuse):
            x = tf.layers.conv2d(
                inputs=x,
                filters=num_filters,
                kernel_size=kernel_size[2],
                name='%s_3' % layer_name,
                strides=stride,
                padding=padding,
                data_format=data_format,
                trainable=training,
                activation=tf.nn.elu,
                use_bias=use_bias)
            x = x + skip
            x = normalization.batch(
                bottom=x,
                name='%s_bn_3' % layer_name,
                data_format=data_format,
                renorm=renorm,
                training=training)

        if include_pool:
            with tf.variable_scope('%s_pool' % layer_name, reuse=reuse):
                x = tf.layers.max_pooling2d(
                    inputs=x,
                    pool_size=(2, 2),
                    strides=(2, 2),
                    padding=padding,
                    data_format='channels_last',
                    name='%s_pool' % layer_name)
    return x


def up_block(
        layer_name,
        bottom,
        skip_activity,
        reuse,
        kernel_size,
        num_filters,
        training,
        stride=[2, 2],
        padding='same',
        renorm=False,
        use_bias=False):
    """Forward block for seung model."""
    with tf.variable_scope('%s_block' % layer_name, reuse=reuse):
        with tf.variable_scope('%s_layer_1' % layer_name, reuse=reuse):
            x = tf.layers.conv2d_transpose(
                inputs=bottom,
                filters=num_filters,
                kernel_size=kernel_size,
                name='%s_1' % layer_name,
                strides=stride,
                padding=padding,
                trainable=training,
                use_bias=use_bias)
            x = x + skip_activity  # Rethink if this is valid
            x = normalization.batch(
                bottom=x,
                name='%s_bn_1' % layer_name,
                renorm=renorm,
                training=training)
            x = tf.nn.elu(x)
    return x
