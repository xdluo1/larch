
import numpy as np
from scipy.optimize import LinearConstraint
from abc import ABC, abstractmethod
import re

class ParametricConstraint(ABC):

    def __init__(self, binding_tol=1e-4):
        self.binding_tol = binding_tol

    def is_binding(self, x):
        return (np.absolute(self.fun(x)) < self.binding_tol)

    @abstractmethod
    def get_parameters(self):
        raise NotImplementedError("abstract base class, use a derived class instead")

    @abstractmethod
    def get_binding_note(self, x):
        raise NotImplementedError("abstract base class, use a derived class instead")

    @abstractmethod
    def fun(self, x):
        raise NotImplementedError("abstract base class, use a derived class instead")

    @abstractmethod
    def jac(self, x):
        raise NotImplementedError("abstract base class, use a derived class instead")

    @abstractmethod
    def link_model(self, model, scale=None):
        raise NotImplementedError("abstract base class, use a derived class instead")

    def as_constraint_dicts(self):
        return [dict(type='ineq', fun=self.fun, jac=self.jac),]


class RatioBound(ParametricConstraint):

    def __init__(self, p_num, p_den, min_ratio=None, max_ratio=None, model=None, scale=10, binding_tol=1e-4):
        super().__init__(binding_tol=binding_tol)
        self.cmax_num = 0
        self.cmax_den = 0
        self.p_num = p_num
        self.p_den = p_den
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.scale = 1
        self.link_model(model, scale)

    def __repr__(self):
        return f"larch.RatioBound({self.p_num},{self.p_den},{self.min_ratio},{self.max_ratio})"

    def link_model(self, model, scale=None):
        if scale is not None:
            self.scale = scale
        if model is not None:
            self.i_num = model.pf.index.get_loc(self.p_num)
            self.i_den = model.pf.index.get_loc(self.p_den)
            self.len = len(model.pf)
            if self.min_ratio is not None:
                scaling = max(self.min_ratio, 1/self.min_ratio) * self.scale
                if model.pf.loc[self.p_den, 'minimum'] >= 0:
                    # positive denominator
                    self.cmin_num = 1 * scaling
                    self.cmin_den = -self.min_ratio * scaling
                elif model.pf.loc[self.p_den, 'maximum'] <= 0:
                    # negative denominator
                    self.cmin_num = -1 * scaling
                    self.cmin_den = self.min_ratio * scaling
                else:
                    raise ValueError('denominator must be bounded to be non-positive or non-negative')
            else:
                self.cmin_num = 0
                self.cmin_den = 0
            if self.max_ratio is not None:
                scaling = max(self.max_ratio, 1/self.max_ratio) * self.scale
                if model.pf.loc[self.p_den, 'minimum'] >= 0:
                    # positive denominator
                    self.cmax_num = -1 * scaling
                    self.cmax_den = self.max_ratio * scaling
                elif model.pf.loc[self.p_den, 'maximum'] <= 0:
                    # negative denominator
                    self.cmax_num = 1 * scaling
                    self.cmax_den = -self.max_ratio * scaling
                else:
                    raise ValueError('denominator must be bounded to be non-positive or non-negative')
            else:
                self.cmax_num = 0
                self.cmax_den = 0

    def _min_fun(self, x):
        return x[self.i_num] * self.cmin_num + x[self.i_den] * self.cmin_den

    def _max_fun(self, x):
        return x[self.i_num] * self.cmax_num + x[self.i_den] * self.cmax_den

    def fun(self, x):
        return min(
            self._min_fun(x),
            self._max_fun(x),
        )

    def jac(self, x):
        j = np.zeros_like(x)
        if self._min_fun(x) < self._max_fun(x):
            j[self.i_num] = self.cmin_num
            j[self.i_den] = self.cmin_den
        else:
            j[self.i_num] = self.cmax_num
            j[self.i_den] = self.cmax_den
        return j

    def get_parameters(self):
        return (self.p_num, self.p_den)

    def get_binding_note(self, x):
        if self._min_fun(x) < self._max_fun(x):
            return f"{self.p_num!s} / {self.p_den!s} ≥ {self.min_ratio}"
        else:
            return f"{self.p_num!s} / {self.p_den!s} ≤ {self.max_ratio}"

    def as_linear_constraints(self):
        a = np.zeros([2,self.len], dtype='float64')
        a[0,self.i_num] = self.cmin_num
        a[0,self.i_den] = self.cmin_den
        a[1,self.i_num] = self.cmax_num
        a[1,self.i_den] = self.cmax_den
        return [LinearConstraint(a, 0, np.inf)]

    def __eq__(self, other):
        if not isinstance(other, RatioBound):
            return False
        if (
                (self.p_num == other.p_num)
                and (self.p_den == other.p_den)
                and (self.min_ratio == other.min_ratio)
                and (self.max_ratio == other.max_ratio)
        ):
            return True
        return False


class OrderingBound(ParametricConstraint):

    def __init__(self, p_less, p_more=None, model=None, scale=10, binding_tol=1e-4):
        if p_more is None:
            if "<=" in p_less:
                p_less, p_more = [_.strip() for _ in p_less.split("<=",1)]
            elif "<" in p_less:
                p_less, p_more = [_.strip() for _ in p_less.split("<", 1)]
            elif ">=" in p_less:
                p_more, p_less = [_.strip() for _ in p_less.split(">=", 1)]
            elif ">" in p_less:
                p_more, p_less = [_.strip() for _ in p_less.split(">", 1)]
            else:
                raise ValueError(f"cannot interpret {p_less} as ordering")
        super().__init__(binding_tol=binding_tol)
        self.p_less = p_less
        self.p_more = p_more
        self.scale = 1
        if model is not None:
            self.len = len(model.pf)
            self.link_model(model, scale)
        else:
            self.len = 0

    def __repr__(self):
        return f"larch.OrderingBound({self.p_less},{self.p_more})"

    def link_model(self, model, scale=None):
        self.i_less = model.pf.index.get_loc(self.p_less)
        self.i_more = model.pf.index.get_loc(self.p_more)
        self.len = len(model.pf)
        if scale is not None:
            self.scale = scale

    def fun(self, x):
        return (x[self.i_more] - x[self.i_less])*self.scale

    def jac(self, x):
        j = np.zeros_like(x)
        j[self.i_more] = self.scale
        j[self.i_less] = -self.scale
        return j

    def get_parameters(self):
        return (self.p_less, self.p_more)

    def get_binding_note(self, x):
        return f"{self.p_less!s} ≤ {self.p_more!s}"

    def as_linear_constraints(self):
        a = np.zeros([1,self.len], dtype='float64')
        a[0,self.i_more] = self.scale
        a[0,self.i_less] = -self.scale
        return [LinearConstraint(a, 0, np.inf)]

    def __eq__(self, other):
        if not isinstance(other, OrderingBound):
            return False
        if (
                (self.p_less == other.p_less)
                and (self.p_more == other.p_more)
        ):
            return True
        return False


class FixedBound(ParametricConstraint):

    def __init__(self, p, minimum=None, maximum=None, model=None, scale=10, binding_tol=1e-4):
        super().__init__(binding_tol=binding_tol)
        self.p = p
        self.minimum = minimum
        self.maximum = maximum
        self.scale = 1
        if model is not None:
            self.link_model(model, scale)

    def __repr__(self):
        return f"larch.FixedBound({self.p},{self.minimum},{self.maximum})"

    def link_model(self, model, scale=None):
        self.i = model.pf.index.get_loc(self.p)
        self.len = len(model.pf)
        if scale is not None:
            self.scale = scale

    def _min_fun(self, x):
        if self.minimum is not None:
            return (x[self.i] - self.minimum) * self.scale
        else:
            return np.inf

    def _max_fun(self, x):
        if self.maximum is not None:
            return (self.maximum - x[self.i]) * self.scale
        else:
            return np.inf

    def fun(self, x):
        return min(
            self._min_fun(x),
            self._max_fun(x),
        )

    def jac(self, x):
        j = np.zeros_like(x)
        if self._min_fun(x) < self._max_fun(x):
            j[self.i] = self.scale
        else:
            j[self.i] = -self.scale
        return j

    def get_parameters(self):
        return (self.p,)

    def get_binding_note(self, x):
        if self._min_fun(x) < self._max_fun(x):
            return f"{self.p!s} ≥ {self.minimum}"
        else:
            return f"{self.p!s} ≤ {self.maximum}"

    def as_linear_constraints(self):
        a = np.zeros([1,self.len], dtype='float64')
        a[0,self.i] = 1
        return [LinearConstraint(
            a,
            self.minimum if self.minimum is not None else -np.inf,
            self.maximum if self.maximum is not None else np.inf,
        )]

    def __eq__(self, other):
        if not isinstance(other, FixedBound):
            return False
        if (
                (self.p == other.p)
                and (self.minimum == other.minimum)
                and (self.maximum == other.maximum)
        ):
            return True
        return False



#######

from collections.abc import MutableSequence

class ParametricConstraintList(MutableSequence):

    def __init__(self, init=None):
        self._cx = list()
        self.allow_dupes = False
        if init is not None:
            for i in init:
                if isinstance(i, ParametricConstraint):
                    self._cx.append(i)
                else:
                    raise TypeError(f'members of {self.__class__.__name__} must be ParametricConstraint')

    def set_instance(self, instance):
        self._instance = instance
        for i in self._cx:
            i.link_model(self._instance)

    def __fresh(self, instance):
        newself = ParametricConstraintList()
        newself._instance = instance
        setattr(instance, self.private_name, newself)
        return newself

    def __get__(self, instance, owner):

        if instance is None:
            return self
        try:
            newself = getattr(instance, self.private_name)
        except AttributeError:
            newself = self.__fresh(instance)
        if newself is None:
            newself = self.__fresh(instance)
        return newself

    def __set__(self, instance, values):

        try:
            newself = getattr(instance, self.private_name)
        except AttributeError:
            newself = self.__fresh(instance)
        if newself is None:
            newself = self.__fresh(instance)
        newself.__init__(values)
        try:
            newself._instance.mangle()
        except AttributeError as err:
            pass
        for i in newself._cx:
            i.link_model(newself._instance)

    def __delete__(self, instance):

        try:
            newself = getattr(instance, self.private_name)
        except AttributeError:
            newself = self.__fresh(instance)
        newself.__init__()
        newself._instance = instance
        try:
            newself._instance.mangle()
        except AttributeError as err:
            pass

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = "_"+name

    def __getitem__(self, item):
        return self._cx[item]

    def __setitem__(self, key:int, value):
        if isinstance(value, str):
            value = interpret_contraint(value)
        if not isinstance(value, ParametricConstraint):
            raise TypeError('items must be of type ParametricConstraint')
        if self.allow_dupes or not self._is_duplicate(value):
            self._cx[key] = value
            try:
                self._instance.mangle()
            except AttributeError as err:
                pass
            self._cx[key].link_model(self._instance)

    def __delitem__(self, key):
        del self._cx[key]
        try:
            self._instance.mangle()
        except AttributeError as err:
            pass

    def __len__(self):
        return len(self._cx)

    def insert(self, index, value):
        if isinstance(value, str):
            value = interpret_contraint(value)
        if not isinstance(value, ParametricConstraint):
            raise TypeError('items must be of type ParametricConstraint')
        if self.allow_dupes or not self._is_duplicate(value):
            self._cx.insert(index, value)
            try:
                self._instance.mangle()
            except AttributeError as err:
                pass
            self._cx[index].link_model(self._instance)

    def __repr__(self):
        return repr(self._cx)

    def _is_duplicate(self, value):
        for i in self._cx:
            if i == value:
                return True
        return False

    def rescale(self, scale=None, index=None):
        if index is None:
            for i in self._cx:
                if scale is None:
                    i.link_model(self._instance, np.exp(np.random.uniform(-3, 3)))
                else:
                    i.link_model(self._instance, scale)
        else:
            if scale is None:
                self._cx[index].link_model(self._instance, np.exp(np.random.uniform(-3, 3)))
            else:
                self._cx[index].link_model(self._instance, scale)


def asfloat(x):
    if "/" in x:
        x_ = x.split("/")
        return float(x_[0])/float(x_[1])
    return float(x)

def interpret_contraint(c):
    numbr = r"\s*([-+]?\d*\.?\d*[eE]?[-+]?\d*|\d+\/\d+)\s*"
    token = r"\s*([\w#:\*&^%\$!@]+)\s*"

    n_2w = f"^{numbr}(<=|<){token}(<=|<){numbr}$"
    rx = re.match(n_2w, c)
    if rx:
        return FixedBound(rx.group(3), minimum=asfloat(rx.group(1)), maximum=asfloat(rx.group(5)))

    le_n = f"^{token}(<=|<){numbr}$"
    rx = re.match(le_n, c)
    if rx:
        return FixedBound(rx.group(1), maximum=asfloat(rx.group(3)))

    ge_n = f"^{token}(>=|>){numbr}$"
    rx = re.match(ge_n, c)
    if rx:
        return FixedBound(rx.group(1), minimum=asfloat(rx.group(3)))

    n_le = f"^{numbr}(<=|<){token}$"
    rx = re.match(n_le, c)
    if rx:
        return FixedBound(rx.group(3), minimum=asfloat(rx.group(1)))

    n_ge = f"^{numbr}(>=|>){token}$"
    rx = re.match(n_ge, c)
    if rx:
        return FixedBound(rx.group(3), maximum=asfloat(rx.group(1)))

    le = f"^{token}(<=|<){token}$"
    rx = re.match(le, c)
    if rx:
        return OrderingBound(rx.group(1), rx.group(3))

    ge = f"^{token}(>=|>){token}$"
    rx = re.match(ge, c)
    if rx:
        return OrderingBound(rx.group(3), rx.group(1))

    r_le = f"^{token}/{token}(<=|<){numbr}$"
    rx = re.match(r_le, c)
    if rx:
        return RatioBound(rx.group(1), rx.group(2), max_ratio=asfloat(rx.group(4)))

    r_ge = f"^{token}/{token}(>=|>){numbr}$"
    rx = re.match(r_ge, c)
    if rx:
        return RatioBound(rx.group(1), rx.group(2), min_ratio=asfloat(rx.group(4)))

    r_2w = f"^{numbr}(<=|<){token}/{token}(<=|<){numbr}$"
    rx = re.match(r_2w, c)
    if rx:
        return RatioBound(rx.group(3), rx.group(4), min_ratio=asfloat(rx.group(1)), max_ratio=asfloat(rx.group(6)))

    raise ValueError(f"cannot interpret '{c}' as a constraint")
