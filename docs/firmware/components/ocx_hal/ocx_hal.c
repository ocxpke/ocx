#include "ocx_hal.h"

const char *ocx_err_str(ocx_err_t e)
{
    switch (e) {
    case OCX_OK: return "OK";
    case OCX_ERR_IO: return "error de bus";
    case OCX_ERR_TIMEOUT: return "timeout";
    case OCX_ERR_ARG: return "argumento invalido";
    case OCX_ERR_STATE: return "estado inesperado";
    }
    return "?";
}
