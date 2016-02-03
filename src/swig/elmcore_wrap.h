/* ----------------------------------------------------------------------------
 * This file was automatically generated by SWIG (http://www.swig.org).
 * Version 3.0.8
 *
 * This file is not intended to be easily readable and contains a number of
 * coding conventions designed to improve portability and efficiency. Do not make
 * changes to this file unless you know what you are doing--modify the SWIG
 * interface file instead.
 * ----------------------------------------------------------------------------- */

#ifndef SWIG_core_WRAP_H_
#define SWIG_core_WRAP_H_

#include <map>
#include <string>


class SwigDirector_Fountain : public elm::Fountain, public Swig::Director {

public:
    SwigDirector_Fountain(PyObject *self);
    virtual elm::VAS_dna ask_dna(long long const &c = 0);
    virtual elm::VAS_dna const ask_dna(long long const &c = 0) const;
    virtual unsigned int nCases() const;
    virtual unsigned int nAlts() const;
    virtual std::vector< std::string,std::allocator< std::string > > alternative_names() const;
    virtual std::vector< long long,std::allocator< long long > > alternative_codes() const;
    virtual std::string alternative_name(long long arg0) const;
    virtual long long alternative_code(std::string arg0) const;
    virtual bool check_ca(std::string const &column) const;
    virtual bool check_co(std::string const &column) const;
    virtual std::vector< std::string,std::allocator< std::string > > variables_ca() const;
    virtual std::vector< std::string,std::allocator< std::string > > variables_co() const;
    virtual ~SwigDirector_Fountain();

/* Internal director utilities */
public:
    bool swig_get_inner(const char *swig_protected_method_name) const {
      std::map<std::string, bool>::const_iterator iv = swig_inner.find(swig_protected_method_name);
      return (iv != swig_inner.end() ? iv->second : false);
    }
    void swig_set_inner(const char *swig_protected_method_name, bool swig_val) const {
      swig_inner[swig_protected_method_name] = swig_val;
    }
private:
    mutable std::map<std::string, bool> swig_inner;

#if defined(SWIG_PYTHON_DIRECTOR_VTABLE)
/* VTable implementation */
    PyObject *swig_get_method(size_t method_index, const char *method_name) const {
      PyObject *method = vtable[method_index];
      if (!method) {
        swig::SwigVar_PyObject name = SWIG_Python_str_FromChar(method_name);
        method = PyObject_GetAttr(swig_get_self(), name);
        if (!method) {
          std::string msg = "Method in class Fountain doesn't exist, undefined ";
          msg += method_name;
          Swig::DirectorMethodException::raise(msg.c_str());
        }
        vtable[method_index] = method;
      }
      return method;
    }
private:
    mutable swig::SwigVar_PyObject vtable[14];
#endif

};


#endif