# -*- coding: utf-8 -*-
"""
Direction Cosine Matrix
=======================

The difference, in three dimensions, between any given orthogonal frame and a
base coordinate frame is the **orientation** or **attitude**.

Rotations are linear operations preserving vector lenght and relative vector
orientation, and a rotation operator acting on a vector :math:`\\mathbf{v}\\in\\mathbb{R}^3`
can be defined in the Special Orthogonal group :math:`SO(3)`, also known as the
**rotation group**.

The rotation operator is, normally, represented by a :math:`3\\times 3` matrix:

.. math::
    \\mathbf{R} =
    \\begin{bmatrix}
    | & | & | \\\\ \\mathbf{r}_1 & \\mathbf{r}_2 & \\mathbf{r}_3 \\\\ | & | & |
    \\end{bmatrix} \\in \\mathbb{R}^{3\\times 3}

where :math:`\\mathbf{r}_1`, :math:`\\mathbf{r}_2` and :math:`\\mathbf{r}_3`
are unit vectors orthogonal to each other. All matrices satisfying this
condition are called **orthogonal matrices**.

The rotation operator :math:`\\mathbf{R}` rotates any vector
:math:`\\mathbf{v}\\in\\mathbb{R}^3` through the matrix product,

.. math::
    \\mathbf{v}' = \\mathbf{Rv}

Thanks to its orthonormality, :math:`\\mathbf{RR}^{-1}=\\mathbf{RR}^T=\\mathbf{R}^T\\mathbf{R}=\\mathbf{I}`,
indicating that the inverse of :math:`\\mathbf{R}` is its transpose. So,

.. math::
    \\mathbf{v} = \\mathbf{R}^T\\mathbf{v}'

The determinant of a rotation matrix is always equal to :math:`+1`. Meaning,
its product with any vector will leave the vector's lenght unchanged.

Matrices conforming to both properties belong to the special orthogonal group
:math:`SO(3)`. Even better, the product of two or more rotation matrices yields another
rotation matrix in :math:`SO(3)`

Direction cosines are cosines of angles between a vector and a base coordinate
frame [WikiDCM]_. In this case, the difference between orthogonal vectors :math:`\\mathbf{r}_i`
and the base frame are describing the Direction Cosines. This orientation
matrix is commonly named the **Direction Cosine Matrix**.

DCMs are, therefore, the most common representation of rotations [WikiR]_,
especially in real applications of spacecraft tracking and location.

Rotations have several representations. The most common to use and easier to
understand are the Direction Cosine Matrices, or Rotation Matrices.

Strictly speaking, a **rotation matrix** is the matrix that, when
pre-multiplied by a vector expressed in the world coordinates, yields the same
vector expressed in the body-fixed coordinates.

A rotation matrix can also be referred to as a *direction cosine matrix*,
because its elements are the cosines of the unsigned angles between body-fixed
axes and the world axes.

References
----------
.. [WikiDCM] Wikipedia: Direction Cosine.
    (https://en.wikipedia.org/wiki/Direction_cosine)
.. [WikiR] Wikipedia: Rotation Matrix
    (https://mathworld.wolfram.com/RotationMatrix.html)
.. [Ma] Yi Ma, Stefano Soatto, Jana Kosecka, and S. Shankar Sastry. An
    Invitation to 3-D Vision: From Images to Geometric Models. Springer
    Verlag. 2003.
    (https://www.eecis.udel.edu/~cer/arv/readings/old_mkss.pdf)
.. [Huyhn] Huynh, D.Q. Metrics for 3D Rotations: Comparison and Analysis. J
    Math Imaging Vis 35, 155–164 (2009).
.. [Curtis] Howard D Curtis. Orbital Mechanics for Engineering Students (Third
    Edition) Butterworth-Heinemann. 2014.
.. [Kuipers] Kuipers, Jack B. Quaternions and Rotation Sequences: A Primer with
    Applications to Orbits, Aerospace and Virtual Reality. Princeton;
    Oxford: Princeton University Press, 1999.
.. [Diebel] Diebel, James. Representing Attitude; Euler Angles, Unit
    Quaternions, and Rotation. Stanford University. 20 October 2006.

"""

from typing import Tuple
import numpy as np
from .mathfuncs import *
from .orientation import rotation
from .orientation import rot_seq
# Functions to convert DCM to quaternion representation
from .orientation import shepperd
from .orientation import hughes
from .orientation import chiaverini
from .orientation import itzhack
from .orientation import sarabandi

class DCM(np.ndarray):
    """
    Direction Cosine Matrix in SO(3)

    Class to represent a Direction Cosine Matrix. It is built from a 3-by-3 
    array, but it can also be built from 3-dimensional vectors representing the
    roll-pitch-yaw angles, a quaternion, or an axis-angle pair representation.

    Parameters
    ----------
    array : array-like, default: None
        Array to build the DCM with.
    q : array-like, default: None
        Quaternion to convert to DCM.
    rpy : array-like, default: None
        Array with roll->pitch->yaw angles.
    euler : tuple, default: None
        Dictionary with a set of angles as a pair of string and array.
    axang : tuple, default: None
        Tuple with an array and a float of the axis and the angle
        representation.

    Attributes
    ----------
    A : numpy.ndarray
        Array with the 3-by-3 direction cosine matrix.

    Examples
    --------
    All DCM are created as an identity matrix, which means no rotation.

    >>> from ahrs import DCM
    >>> DCM()
    DCM([[1., 0., 0.],
         [0., 1., 0.],
         [0., 0., 1.]])

    A rotation around a single axis can be defined by giving the desired axis
    and its value, in degrees.

    >>> DCM(x=10.0)
    DCM([[ 1.        ,  0.        ,  0.        ],
         [ 0.        ,  0.98480775, -0.17364818],
         [ 0.        ,  0.17364818,  0.98480775]])
    >>> DCM(y=20.0)
    DCM([[ 0.93969262,  0.        ,  0.34202014],
         [ 0.        ,  1.        ,  0.        ],
         [-0.34202014,  0.        ,  0.93969262]])
    >>> DCM(z=30.0)
    DCM([[ 0.8660254, -0.5      ,  0.       ],
         [ 0.5      ,  0.8660254,  0.       ],
         [ 0.       ,  0.       ,  1.       ]])

    If we want a rotation conforming the roll-pitch-yaw sequence, we can give
    the corresponding angles.

    >>> DCM(rpy=[30.0, 20.0, 10.0])
    DCM([[ 0.81379768, -0.44096961,  0.37852231],
         [ 0.46984631,  0.88256412,  0.01802831],
         [-0.34202014,  0.16317591,  0.92541658]])

    .. note::
        Notice the angles are given in reverse order, as it is the way the
        matrices are multiplied.

    >>> DCM(z=30.0)@DCM(y=20.0)@DCM(x=10.0)
    DCM([[ 0.81379768, -0.44096961,  0.37852231],
         [ 0.46984631,  0.88256412,  0.01802831],
         [-0.34202014,  0.16317591,  0.92541658]])

    But also a different sequence can be defined, if given as a tuple with two
    elements: the order of the axis to rotate about, and the value of the
    rotation angles (again in reverse order)

    >>> DCM(euler=('zyz', [40.0, 50.0, 60.0]))
    DCM([[-0.31046846, -0.74782807,  0.58682409],
         [ 0.8700019 ,  0.02520139,  0.49240388],
         [-0.38302222,  0.66341395,  0.64278761]])
    >>> DCM(z=40.0)@DCM(y=50.0)@DCM(z=60.0)
    DCM([[-0.31046846, -0.74782807,  0.58682409],
         [ 0.8700019 ,  0.02520139,  0.49240388],
         [-0.38302222,  0.66341395,  0.64278761]])

    Another option is to build the rotation matrix from a quaternion:

    >>> DCM(q=[1., 2., 3., 4.])
    DCM([[-0.66666667,  0.13333333,  0.73333333],
         [ 0.66666667, -0.33333333,  0.66666667],
         [ 0.33333333,  0.93333333,  0.13333333]])

    The quaternions are automatically normalized to make them versors and be
    used as rotation operators.

    Finally, we can also build the rotation matrix from an axis-angle
    representation:

    >>> DCM(axang=([1., 2., 3.], 60.0))
    DCM([[-0.81295491,  0.52330834,  0.25544608],
         [ 0.03452394, -0.3945807 ,  0.91821249],
         [ 0.58130234,  0.75528436,  0.30270965]])

    The axis of rotation is also normalized to be used as part of the rotation
    operator.

    """
    def __new__(subtype, array: np.ndarray = None, **kwargs):
        if array is None:
            array = np.identity(3)
            if 'q' in kwargs:
                array = DCM.from_q(DCM, np.array(kwargs.pop('q')))
            if any(x.lower() in ['x', 'y', 'z'] for x in kwargs):
                array = np.identity(3)
                array = array@rotation('x', kwargs.pop('x', 0.0))
                array = array@rotation('y', kwargs.pop('y', 0.0))
                array = array@rotation('z', kwargs.pop('z', 0.0))
            if 'rpy' in kwargs:
                array = rot_seq('zyx', kwargs.pop('rpy'))
            if 'euler' in kwargs:
                seq, angs = kwargs.pop('euler')
                array = rot_seq(seq, angs)
            if 'axang' in kwargs:
                ax, ang = kwargs.pop('axang')
                array = DCM.from_axisangle(DCM, np.array(ax), ang)
        if array.shape[-2:]!=(3, 3):
            raise ValueError("Direction Cosine Matrix must have shape (3, 3) or (N, 3, 3), got {}.".format(array.shape))
        in_SO3 = np.isclose(np.linalg.det(array), 1.0)
        in_SO3 &= np.allclose(array@array.T, np.identity(3))
        if not in_SO3:
            raise ValueError("Given attitude is not in SO(3)")
        # Create the ndarray instance of type DCM. This will call the standard
        # ndarray constructor, but return an object of type DCM.
        obj = super(DCM, subtype).__new__(subtype, array.shape, float, array)
        obj.A = array
        return obj

    @property
    def I(self) -> np.ndarray:
        return self.A.T

    @property
    def inv(self) -> np.ndarray:
        return self.A.T

    @property
    def det(self) -> float:
        return np.linalg.det(self.A)

    @property
    def fro(self) -> float:
        return np.linalg.norm(self.A, 'fro')

    @property
    def frobenius(self) -> float:
        return np.linalg.norm(self.A, 'fro')

    @property
    def log(self) -> np.ndarray:
        """
        Logarithm of DCM

        Returns
        -------
        log : numpy.ndarray
            Logarithm of DCM

        """
        S = 0.5*(self.A-self.A.T)       # Skew-symmetric matrix
        y = np.array([S[2, 1], -S[2, 0], S[1, 0]])  # Axis
        if np.allclose(np.zeros(3), y):
            return np.zeros(3)
        y2 = np.linalg.norm(y)
        return np.arcsin(y2)*y/y2

    @property
    def adjugate(self) -> np.ndarray:
        return np.linalg.det(self.A)*self.A.T

    @property
    def adj(self) -> np.ndarray:
        return np.linalg.det(self.A)*self.A.T

    def to_axisangle(self) -> Tuple[np.ndarray, float]:
        """
        DCM from axis-angle representation

        Use Rodrigue's formula to obtain the axis-angle representation from the
        DCM.

        Parameters
        ----------
        axis : numpy.ndarray
            Axis of rotation.
        angle : float
            Angle of rotation.

        """
        angle = np.arccos((self.A.trace()-1)/2)
        axis = np.zeros(3)
        if angle!=0:
            axis = np.array([self.A[2, 1]-self.A[1, 2], self.A[0, 2]-self.A[2, 0], self.A[1, 0]-self.A[0, 1]])/(2*np.sin(angle))
        return axis, angle

    def to_axang(self) -> Tuple[np.ndarray, float]:
        """Synonym of method ``to_axisangle``
        """
        return self.to_axisangle()

    def from_axisangle(self, axis: np.ndarray, angle: float) -> np.ndarray:
        """
        DCM from axis-angle representation

        Use Rodrigue's formula to obtain the DCM from the axis-angle
        representation.

        Parameters
        ----------
        axis : numpy.ndarray
            Axis of rotation.
        angle : float
            Angle of rotation.

        Returns
        -------
        R : numpy.ndarray
            3-by-3 direction cosine matrix

        """
        axis /= np.linalg.norm(axis)
        K = skew(axis)
        return np.identity(3) + np.sin(angle)*K + (1-np.cos(angle))*K@K

    def from_quaternion(self, q: np.ndarray) -> np.ndarray:
        """
        DCM from given quaternion

        The quaternion :math:`\\mathbf{q}` has the form :math:`\\mathbf{q} = (q_w, q_x, q_y, q_z)`,
        where :math:`\\mathbf{q}_v = (q_x, q_y, q_z)` is the vector part, and
        :math:`q_w` is the scalar part.

        The resulting matrix :math:`\\mathbf{R}` has the form:

        .. math::

            \\mathbf{R}(\\mathbf{q}) =
            \\begin{bmatrix}
            1 - 2(q_y^2 + q_z^2) & 2(q_xq_y - q_wq_z) & 2(q_xq_z + q_wq_y) \\\\
            2(q_xq_y + q_wq_z) & 1 - 2(q_x^2 + q_z^2) & 2(q_yq_z - q_wq_x) \\\\
            2(q_xq_z - q_wq_y) & 2(q_wq_x + q_yq_z) & 1 - 2(q_x^2 + q_y^2)
            \\end{bmatrix}

        The identity Quaternion :math:`\\mathbf{q} = (1, 0, 0, 0)`, produces a
        a :math:`3 \\times 3` Identity matrix :math:`\\mathbf{I}_3`.

        Returns
        -------
        R : numpy.ndarray
            3-by-3 direction cosine matrix

        """
        if q is None:
            return np.identity(3)
        if q.shape[-1]!=4 or q.ndim>2:
            raise ValueError("Quaternion must be of the form (4,) or (N, 4)")
        if q.ndim>1:
            q /= np.linalg.norm(q, axis=1)[:, None]     # Normalize
            R = np.zeros((q.shape[0], 3, 3))
            R[:, 0, 0] = 1.0 - 2.0*(q[:, 2]**2 + q[:, 3]**2)
            R[:, 1, 0] = 2.0*(q[:, 1]*q[:, 2]+q[:, 0]*q[:, 3])
            R[:, 2, 0] = 2.0*(q[:, 1]*q[:, 3]-q[:, 0]*q[:, 2])
            R[:, 0, 1] = 2.0*(q[:, 1]*q[:, 2]-q[:, 0]*q[:, 3])
            R[:, 1, 1] = 1.0 - 2.0*(q[:, 1]**2 + q[:, 3]**2)
            R[:, 2, 1] = 2.0*(q[:, 0]*q[:, 1]+q[:, 2]*q[:, 3])
            R[:, 0, 2] = 2.0*(q[:, 1]*q[:, 3]+q[:, 0]*q[:, 2])
            R[:, 1, 2] = 2.0*(q[:, 2]*q[:, 3]-q[:, 0]*q[:, 1])
            R[:, 2, 2] = 1.0 - 2.0*(q[:, 1]**2 + q[:, 2]**2)
            return R
        q /= np.linalg.norm(q)
        return np.array([
            [1.0-2.0*(q[2]**2+q[3]**2), 2.0*(q[1]*q[2]-q[0]*q[3]), 2.0*(q[1]*q[3]+q[0]*q[2])],
            [2.0*(q[1]*q[2]+q[0]*q[3]), 1.0-2.0*(q[1]**2+q[3]**2), 2.0*(q[2]*q[3]-q[0]*q[1])],
            [2.0*(q[1]*q[3]-q[0]*q[2]), 2.0*(q[0]*q[1]+q[2]*q[3]), 1.0-2.0*(q[1]**2+q[2]**2)]])

    def from_q(self, q: np.ndarray) -> np.ndarray:
        """Synonym of method ``from_quaternion``
        """
        return self.from_quaternion(self, q)

    def to_quaternion(self, method: str = 'chiaverini', **kw) -> np.ndarray:
        """
        Quaternion from Direction Cosine Matrix.

        There are five methods available to obtain a quaternion from a
        Direction Cosine Matrix:

        * ``'chiaverini'`` as described in [Chiaverini]_
        * ``'hughes'`` as described in [Hughes]_
        * ``'itzhack'`` as described in [Bar-Itzhack]_
        * ``'sarabandi'`` as described in [Sarabandi]_
        * ``'shepperd'`` as described in [Shepperd]_

        Parameters
        ----------
        dcm : numpy.ndarray
            3-by-3 Direction Cosine Matrix.
        method : str, default: 'chiaverini'
            Method to use. Options are: 'chiaverini', 'hughes', 'itzhack',
            'sarabandi', and 'shepperd'.

        """
        q = np.array([1., 0., 0., 0.])
        if method.lower()=='hughes':
            q = hughes(self.A)
        if method.lower()=='chiaverini':
            q = chiaverini(self.A)
        if method.lower()=='shepperd':
            q = shepperd(self.A)
        if method.lower()=='itzhack':
            q = itzhack(self.A, version=kw.get('version', 3))
        if method.lower()=='sarabandi':
            q = sarabandi(self.A, eta=kw.get('threshold', 0.0))
        return q/np.linalg.norm(q)

    def to_q(self, method: str = 'chiaverini', **kw) -> np.ndarray:
        """Synonym of method ``to_quaternion``
        """
        return self.to_quaternion(method=method, **kw)

    def to_angles(self) -> np.ndarray:
        """
        Euler Angles from DCM

        Returns
        -------
        e : numpy.ndarray
            Euler angles
        """
        phi = np.arctan2(self.A[1, 2], self.A[2, 2])    # Roll Angle
        theta = -np.sin(self.A[0, 2])                   # Pitch Angle
        psi = np.arctan2(self.A[0, 1], self.A[0, 0])    # Yaw Angle
        return np.array([phi, theta, psi])

    def ode(self, w: np.ndarray) -> np.ndarray:
        """
        Ordinary Differential Equation of the DCM.

        Parameters
        ----------
        w : numpy.ndarray
            Angular velocity, in rad/s, about X-, Y- and Z-axis.

        Returns
        -------
        dR/dt : numpy.ndarray
            Derivative of DCM
        """
        return self.A@skew(w)
