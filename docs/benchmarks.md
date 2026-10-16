# `dynapydantic` Benchmarks

This page shows the results of local benchmarking of this library.
Absolute performance is largely governed by pydantic-core, so the
figures reported here are measurments over a hand-rolled equivalent
solution.

### Legend
* MC = Model-construction time union realization
* VT = Validation-time union realization
* Disc = Discriminated union
* Smart = Smart union

## Class hierarchy creation overhead (median ± IQR) <a id="registration"></a>

<table class="benchmark-table">
  <thead>
    <tr>
      <th rowspan="2">Mode</th>
     <th colspan="3" scope="colgroup">Subclass Count</th>
    </tr>
    <tr>
      <th>5</th>
      <th>25</th>
      <th>100</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Disc MC</th>
      <td>0.413 ± 0.044 ms<br>22.34% ± 2.41%</td>
      <td>1.818 ± 0.106 ms<br>23.29% ± 1.38%</td>
      <td>6.993 ± 0.261 ms<br>23.20% ± 0.87%</td>
    </tr>
    <tr>
      <th>Disc VT</th>
      <td>40.688 ± 34.642 us<br>2.20% ± 1.87%</td>
      <td>0.424 ± 0.113 ms<br>5.44% ± 1.44%</td>
      <td>2.395 ± 0.605 ms<br>7.94% ± 2.01%</td>
    </tr>
    <tr>
      <th>Disc MC<br>Injected</th>
      <td>0.970 ± 0.043 ms<br>52.49% ± 2.43%</td>
      <td>4.510 ± 0.132 ms<br>57.78% ± 1.80%</td>
      <td>17.971 ± 0.452 ms<br>59.60% ± 1.53%</td>
    </tr>
    <tr>
      <th>Disc VT<br>Injected</th>
      <td>0.594 ± 0.052 ms<br>32.12% ± 2.87%</td>
      <td>3.315 ± 0.123 ms<br>42.47% ± 1.64%</td>
      <td>13.223 ± 0.304 ms<br>43.86% ± 1.03%</td>
    </tr>
    <tr>
      <th>Smart MC</th>
      <td>0.298 ± 0.041 ms<br>17.51% ± 2.41%</td>
      <td>1.078 ± 0.070 ms<br>14.29% ± 0.93%</td>
      <td>3.891 ± 0.305 ms<br>13.16% ± 1.04%</td>
    </tr>
    <tr>
      <th>Smart VT</th>
      <td>0.167 ± 0.030 ms<br>9.84% ± 1.79%</td>
      <td>0.593 ± 0.078 ms<br>7.86% ± 1.03%</td>
      <td>2.017 ± 0.383 ms<br>6.82% ± 1.30%</td>
    </tr>
  </tbody>
</table>

## Validation overhead per validation (median ± IQR; 10 subclasses) <a id="validation"></a>

<table class="benchmark-table">
  <thead>
    <tr>
      <th rowspan="2" scope="col">Mode</th>
      <th scope="col">Python (N=1)</th>
      <th scope="col">Python (N=1000)</th>
      <th scope="col">JSON (N=1)</th>
      <th scope="col">JSON (N=1000)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">Disc MC</th>
      <td>0.459 ± 0.358 us<br>8.54% ± 6.67%</td>
      <td>0.023 ± 0.049 us<br>1.15% ± 2.46%</td>
      <td>0.499 ± 0.325 us<br>9.36% ± 6.11%</td>
      <td>0.010 ± 0.030 us<br>0.52% ± 1.59%</td>
    </tr>
    <tr>
      <th scope="row">Disc VT</th>
      <td>0.667 ± 0.008 ms<br>12402.33% ± 506.21%</td>
      <td>7.831 ± 0.088 us<br>394.49% ± 8.10%</td>
      <td>0.672 ± 0.008 ms<br>12596.06% ± 511.85%</td>
      <td>11.167 ± 0.102 us<br>590.28% ± 7.00%</td>
    </tr>
    <tr>
      <th scope="row">Smart MC</th>
      <td>0.625 ± 1.266 us<br>3.88% ± 7.85%</td>
      <td>0.005 ± 0.132 us<br>0.04% ± 1.19%</td>
      <td>0.458 ± 0.502 us<br>3.45% ± 3.77%</td>
      <td>0.050 ± 0.087 us<br>0.55% ± 0.97%</td>
    </tr>
    <tr>
      <th scope="row">Smart VT</th>
      <td>0.229 ± 0.003 ms<br>1423.13% ± 83.28%</td>
      <td>7.886 ± 0.164 us<br>70.78% ± 1.59%</td>
      <td>0.236 ± 0.004 ms<br>1777.22% ± 52.31%</td>
      <td>11.445 ± 0.120 us<br>127.38% ± 1.73%</td>
    </tr>
  </tbody>
</table>
