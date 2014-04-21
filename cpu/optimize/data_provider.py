__author__ = 'mdenil'

import numpy as np
import random
from collections import OrderedDict

from cpu import space

class MinibatchDataProvider(object):
    def __init__(self, X, Y, lengths, batch_size):
        self.X = X
        self.Y = Y
        self.lengths = lengths
        self.batch_size = batch_size

        self._batch_index = -1 # will be incremented to 0 when next_batch is called
        self.batches_per_epoch = int(self.X.shape[0] / self.batch_size)

    def next_batch(self):
        self._prepare_for_next_batch()

        batch_start = self._batch_index * self.batch_size
        batch_end = batch_start + self.batch_size

        X_batch = self.X[batch_start:batch_end]
        Y_batch = self.Y[batch_start:batch_end]
        lengths_batch = self.lengths[batch_start:batch_end]

        meta = {
            'lengths': lengths_batch,
            'space_below': space.Space.infer(X_batch, axes=['b', 'w']),
            }

        return X_batch, Y_batch, meta

    def _prepare_for_next_batch(self):
        self._batch_index = (self._batch_index + 1) % self.batches_per_epoch

        if self._batch_index == 0:
            self._shuffle_data()

    def _shuffle_data(self):
        perm = np.random.permutation(self.X.shape[0])
        self.X = self.X[perm]
        self.Y = self.Y[perm]
        self.lengths = self.lengths[perm]



class BatchDataProvider(object):
    def __init__(self, X, Y, lengths):
        self.X = X
        self.Y = Y
        self.lengths = lengths

        self.batch_size = X.shape[0]
        self.batches_per_epoch = 1

    def next_batch(self):
        meta = {
            'lengths': self.lengths,
            'space_below': space.Space.infer(self.X, axes=['b', 'w'])
        }

        return self.X, self.Y, meta


class PaddedSequenceMinibatchProvider(object):
    def __init__(self, X, batch_size, padding, shuffle=True):
        self.X = X
        self.batch_size = batch_size
        self.padding = padding
        self.shuffle = shuffle

        self._batch_index = -1 # will be incremeted to 0 when next_batch is called
        self.batches_per_epoch = len(X) / self.batch_size

    def next_batch(self):
        self._prepare_for_next_batch()

        batch_start = self._batch_index * self.batch_size
        batch_end = batch_start + self.batch_size

        X_batch = self.X[batch_start:batch_end]

        lengths_batch = np.asarray(map(len, X_batch))
        max_length_batch = lengths_batch.max()

        X_batch = np.vstack([np.atleast_2d(self._add_padding(x, max_length_batch)) for x in X_batch])

        meta = {
            'lengths': lengths_batch,
            'space_below': space.Space.infer(X_batch, axes=['b', 'w'])
        }

        return X_batch, meta

    def _add_padding(self, x, length):
        return x + [self.padding] * (length - len(x))

    def _prepare_for_next_batch(self):
        self._batch_index = (self._batch_index + 1) % self.batches_per_epoch

        if self._batch_index == 0 and self.shuffle:
            self._shuffle_data()

    def _shuffle_data(self):
        random.shuffle(self.X)


class LabelledSequenceMinibatchProvider(object):
    def __init__(self, X, Y, batch_size, padding, shuffle=True):
        self.X = X
        self.Y = Y
        self.batch_size = batch_size
        self.padding = padding
        self.shuffle = shuffle

        self._batch_index = -1
        self.batches_per_epoch = len(X) / batch_size

    def next_batch(self):
        self._prepare_for_next_batch()

        batch_start = self._batch_index * self.batch_size
        batch_end = batch_start + self.batch_size

        X_batch = self.X[batch_start:batch_end]
        Y_batch = self.Y[batch_start:batch_end]

        Y_batch = np.equal.outer(Y_batch, np.arange(np.max(Y_batch)+1)).astype(np.float)


        lengths_batch = np.asarray(map(len, X_batch))
        max_length_batch = int(lengths_batch.max())

        X_batch = [self._add_padding(x, max_length_batch) for x in X_batch]

        meta = {
            'lengths': lengths_batch,
            'space_below': space.Space(axes=['b', 'w'], extent=OrderedDict([('b', len(X_batch)), ('w', max_length_batch)]))
        }

        return X_batch, Y_batch, meta

    def _prepare_for_next_batch(self):
        self._batch_index = (self._batch_index + 1) % self.batches_per_epoch

        if self._batch_index == 0 and self.shuffle:
            self._shuffle_data()

    def _shuffle_data(self):
        combined = zip(self.X, self.Y)
        random.shuffle(combined)
        self.X, self.Y = map(list, zip(*combined))

    def _add_padding(self, x, max_length):
        return x + [self.padding] * (max_length - len(x))