from scipy import interpolate as interp


def to_float(s):
    return float(s.replace(',', '.'))


def interpolate(x_measured, y_measured, x_ideal, method = 'interp1d'):
    if method == 'interp1d':
        f = interp.interp1d(x_measured, y_measured,
                bounds_error=False,
                fill_value="extrapolate")
        return f(x_ideal)
    if method == 'CubicSpline':
        f = interp.CubicSpline(x_measured, y_measured,
                extrapolate=True)
        return f(x_ideal)
    if method == 'Akima1DInterpolator':
        f = interp.Akima1DInterpolator(x_measured, y_measured)
        return f(x_ideal)
    else:
        raise Exception('Unimplemented Interpolation method "' + method +  '". Implement in pylabhelper/math.py')