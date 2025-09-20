#include <Python.h>
#include "lzo-2.10/include/lzo/lzo1x.h"

// Fonction C : add
static PyObject *py_add(PyObject *self, PyObject *args)
{
    int a, b;
    if (!PyArg_ParseTuple(args, "ii", &a, &b))
    {
        return NULL;
    }
    return PyLong_FromLong(a + b);
}

// Méthodes exposées
static PyMethodDef GbxMethods[] = {
    {"add", py_add, METH_VARARGS, "Additionne deux entiers."},
    {NULL, NULL, 0, NULL}};

// Module
static struct PyModuleDef gbxmodule = {
    PyModuleDef_HEAD_INIT,
    "_gbx", // nom interne
    "Module gbx en C",
    -1,
    GbxMethods};

PyMODINIT_FUNC PyInit_lzo(void)
{
    return PyModule_Create(&gbxmodule);
}
