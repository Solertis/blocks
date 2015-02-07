from abc import ABCMeta, abstractmethod

import six
from six import add_metaclass


@add_metaclass(ABCMeta)
class IterationScheme(object):
    """An iteration scheme.

    Iteration schemes provide a dataset-agnostic iteration scheme, such as
    sequential batches, shuffled batches, etc. for datasets that choose to
    support them.

    Notes
    -----
    Iteration schemes implement the :meth:`get_request_iterator` method,
    which returns an iterator type (e.g. a generator or a class which
    implements the `iterator protocol`_).

    Stochastic iteration schemes should generally not be shared between
    different data schemes, because it would make experiments harder to
    reproduce.

    .. _iterator protocol:
       https://docs.python.org/3.3/library/stdtypes.html#iterator-types

    """
    @abstractmethod
    def get_request_iterator(self):
        raise NotImplementedError


@add_metaclass(ABCMeta)
class BatchSizeScheme(IterationScheme):
    """Iteration scheme that returns batch sizes.

    For infinite datasets it doesn't make sense to provide indices to
    examples, but the number of samples per batch can still be given.
    Hence BatchSizeScheme is the base class for iteration schemes
    that only provide the number of examples that should be in a batch.

    """
    pass


@add_metaclass(ABCMeta)
class BatchScheme(IterationScheme):
    """Iteration schemes that return slices or indices for batches.

    For datasets where the number of examples is known and easily
    accessible (as is the case for most datasets which are small enough
    to be kept in memory, like MNIST) we can provide slices or lists of
    labels to the dataset.

    """
    pass


class ConstantScheme(BatchSizeScheme):
    """Constant batch size iterator.

    This subset iterator simply returns the same constant batch size
    for a given number of times (or else infinitely).

    Parameters
    ----------
    batch_size : int
        The size of the batch to return.
    num_examples : int, optional
        If given, the request iterator will return `batch_size` until the
        sum reaches `num_exampes`. Note that this means that the last batch
        size returned could be smaller than `batch_size`. If you want to
        ensure all batches are of equal size, then pass `times` equal to
        ``num_examples / batch-size`` instead.
    times : int, optional
        The number of times to return `batch_size`.

    """
    def __init__(self, batch_size, num_examples=None, times=None):
        if num_examples and times:
            raise ValueError
        self.batch_size = batch_size
        self.num_examples = num_examples
        self.times = times

    def get_request_iterator(self):
        return ConstantIterator(self.batch_size, self.num_examples, self.times)


class ConstantIterator(six.Iterator):
    def __init__(self, batch_size, num_examples=None, times=None):
        if num_examples is not None and times is not None:
            raise ValueError
        if times is not None or num_examples is not None:
            if not (times >= 1 or num_examples >= 1):
                raise ValueError
            self.current = 0

        self.batch_size = batch_size
        self.num_examples = num_examples
        self.times = times

    def __iter__(self):
        return self

    def __next__(self):
        if self.times or self.num_examples:
            if self.current == self.times:
                raise StopIteration
            if self.times:
                self.current += 1
            else:
                self.current += self.batch_size
                return min(self.batch_size, self.num_examples - self.current)
        return self.batch_size


class SequentialScheme(BatchScheme):
    """Sequential batches iterator.

    Iterate over all the examples in a dataset of fixed size sequentially
    in batches of a given size.

    Notes
    -----
    The batch size isn't enforced, so the last batch could be smaller.

    """
    def __init__(self, num_examples, batch_size):
        self.num_examples = num_examples
        self.batch_size = batch_size

    def get_request_iterator(self):
        return SequentialIterator(self.num_examples, self.batch_size)


class SequentialIterator(six.Iterator):
    def __init__(self, num_examples, batch_size):
        self.num_examples = num_examples
        self.batch_size = batch_size
        self.current = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.current >= self.num_examples:
            raise StopIteration
        slice_ = range(self.current, min(self.num_examples,
                                         self.current + self.batch_size))
        self.current += self.batch_size
        return slice_
