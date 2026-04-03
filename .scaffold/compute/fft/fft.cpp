/**
 * .scaffold/compute/fft/fft.cpp
 * C++ FFT wrapper — FFTW3 backend for high-performance transforms.
 *
 * Dependencies: libfftw3 (apt install libfftw3-dev / brew install fftw)
 *
 * Build:
 *   g++ -std=c++20 -O2 fft.cpp -lfftw3 -lm -o fft
 *   cmake: target_link_libraries(${TARGET} fftw3)
 */

#pragma once

#include <vector>
#include <complex>
#include <cmath>
#include <stdexcept>

// If FFTW3 is available, use it. Otherwise fall back to a simple DFT.
#ifdef USE_FFTW
#include <fftw3.h>
#endif

namespace scaffold::fft {

using Complex = std::complex<double>;

/**
 * Simple radix-2 Cooley-Tukey FFT.
 * For production, prefer FFTW (set USE_FFTW). This is the fallback.
 */
inline void fft_inplace(std::vector<Complex>& x) {
    const size_t n = x.size();
    if (n <= 1) return;
    if (n & (n - 1)) throw std::invalid_argument("FFT size must be power of 2");

    // Bit-reversal permutation
    for (size_t i = 1, j = 0; i < n; i++) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(x[i], x[j]);
    }

    // Butterfly
    for (size_t len = 2; len <= n; len <<= 1) {
        double angle = -2.0 * M_PI / len;
        Complex wn(cos(angle), sin(angle));
        for (size_t i = 0; i < n; i += len) {
            Complex w(1.0);
            for (size_t j = 0; j < len / 2; j++) {
                Complex u = x[i + j];
                Complex v = x[i + j + len / 2] * w;
                x[i + j] = u + v;
                x[i + j + len / 2] = u - v;
                w *= wn;
            }
        }
    }
}

/**
 * Forward FFT. Returns complex spectrum.
 */
inline std::vector<Complex> fft(const std::vector<double>& signal) {
    // Pad to next power of 2
    size_t n = 1;
    while (n < signal.size()) n <<= 1;

    std::vector<Complex> x(n);
    for (size_t i = 0; i < signal.size(); i++) x[i] = signal[i];

    fft_inplace(x);
    return x;
}

/**
 * Inverse FFT.
 */
inline std::vector<Complex> ifft(std::vector<Complex> spectrum) {
    // Conjugate → FFT → conjugate → scale
    for (auto& c : spectrum) c = std::conj(c);
    fft_inplace(spectrum);
    for (auto& c : spectrum) c = std::conj(c) / static_cast<double>(spectrum.size());
    return spectrum;
}

/**
 * Magnitude of complex spectrum.
 */
inline std::vector<double> magnitude(const std::vector<Complex>& spectrum) {
    std::vector<double> result(spectrum.size());
    for (size_t i = 0; i < spectrum.size(); i++) result[i] = std::abs(spectrum[i]);
    return result;
}

/**
 * Power spectral density.
 */
inline std::vector<double> power_spectrum(const std::vector<double>& signal) {
    auto spec = fft(signal);
    std::vector<double> psd(spec.size());
    for (size_t i = 0; i < spec.size(); i++) {
        psd[i] = std::norm(spec[i]) / signal.size();
    }
    return psd;
}

#ifdef USE_FFTW
/**
 * FFTW3-backed FFT. Use this for production — significantly faster.
 */
inline std::vector<Complex> fft_fftw(const std::vector<double>& signal) {
    int n = signal.size();
    int out_n = n / 2 + 1;

    auto* in = fftw_alloc_real(n);
    auto* out = fftw_alloc_complex(out_n);

    std::copy(signal.begin(), signal.end(), in);

    fftw_plan plan = fftw_plan_dft_r2c_1d(n, in, out, FFTW_ESTIMATE);
    fftw_execute(plan);

    std::vector<Complex> result(out_n);
    for (int i = 0; i < out_n; i++) {
        result[i] = Complex(out[i][0], out[i][1]);
    }

    fftw_destroy_plan(plan);
    fftw_free(in);
    fftw_free(out);
    return result;
}
#endif

} // namespace scaffold::fft
