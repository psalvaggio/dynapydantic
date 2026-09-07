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
      <td>0.438 ± 0.070 ms<br>18.93% ± 3.05%</td>
      <td>1.909 ± 0.116 ms<br>19.20% ± 1.18%</td>
      <td>7.243 ± 0.417 ms<br>18.80% ± 1.09%</td>
    </tr>
    <tr>
      <th>Disc VT</th>
      <td>-59.396 ± 57.477 us<br>-2.56% ± 2.48%</td>
      <td>61.480 ± 106.507 us<br>0.62% ± 1.07%</td>
      <td>0.764 ± 0.418 ms<br>1.98% ± 1.08%</td>
    </tr>
    <tr>
      <th>Disc MC<br>Injected</th>
      <td>0.991 ± 0.062 ms<br>42.76% ± 2.82%</td>
      <td>4.966 ± 0.132 ms<br>49.94% ± 1.38%</td>
      <td>19.138 ± 0.421 ms<br>49.68% ± 1.17%</td>
    </tr>
    <tr>
      <th>Disc VT<br>Injected</th>
      <td>0.549 ± 0.059 ms<br>23.70% ± 2.58%</td>
      <td>2.991 ± 0.124 ms<br>30.08% ± 1.27%</td>
      <td>12.351 ± 0.514 ms<br>32.06% ± 1.36%</td>
    </tr>
    <tr>
      <th>Smart MC</th>
      <td>0.303 ± 0.056 ms<br>14.00% ± 2.57%</td>
      <td>1.270 ± 0.322 ms<br>13.05% ± 3.31%</td>
      <td>4.199 ± 2.273 ms<br>11.05% ± 5.98%</td>
    </tr>
    <tr>
      <th>Smart VT</th>
      <td>0.281 ± 0.300 ms<br>12.97% ± 13.85%</td>
      <td>92.812 ± 155.072 us<br>0.95% ± 1.59%</td>
      <td>0.712 ± 0.378 ms<br>1.87% ± 0.99%</td>
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
      <td>0.418 ± 0.324 us<br>7.38% ± 5.74%</td>
      <td>0.041 ± 0.032 us<br>2.03% ± 1.58%</td>
      <td>0.375 ± 0.301 us<br>6.67% ± 5.35%</td>
      <td>0.028 ± 0.030 us<br>1.43% ± 1.55%</td>
    </tr>
    <tr>
      <th scope="row">Disc VT</th>
      <td>0.888 ± 0.011 ms<br>15677.59% ± 714.44%</td>
      <td>8.072 ± 0.072 us<br>397.82% ± 5.59%</td>
      <td>0.888 ± 0.010 ms<br>15785.18% ± 501.44%</td>
      <td>11.511 ± 0.229 us<br>589.69% ± 13.19%</td>
    </tr>
    <tr>
      <th scope="row">Smart MC</th>
      <td>0.250 ± 0.742 us<br>1.53% ± 4.56%</td>
      <td>0.080 ± 0.200 us<br>0.70% ± 1.74%</td>
      <td>0.708 ± 0.569 us<br>5.04% ± 4.05%</td>
      <td>0.022 ± 0.140 us<br>0.23% ± 1.47%</td>
    </tr>
    <tr>
      <th scope="row">Smart VT</th>
      <td>0.422 ± 0.008 ms<br>2591.76% ± 105.40%</td>
      <td>8.032 ± 0.176 us<br>70.05% ± 1.74%</td>
      <td>0.428 ± 0.009 ms<br>3048.14% ± 105.74%</td>
      <td>11.315 ± 0.227 us<br>118.71% ± 2.92%</td>
    </tr>
  </tbody>
</table>
