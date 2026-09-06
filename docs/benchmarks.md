# `dynapydantic` Benchmarks

### Legend
* MC = Model-construction time union realization
* VT = Validation-time union realization
* Disc = Discriminated union
* Smart = Smart union

## Class hierarchy creation (median ± IQR) <a id="registration"></a>

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
      <td>0.441 ± 0.048 ms<br>19.28% ± 2.14%</td>
      <td>1.838 ± 0.102 ms<br>18.55% ± 1.04%</td>
      <td>7.239 ± 0.373 ms<br>18.92% ± 0.98%</td>
    </tr>
    <tr>
      <th>Disc VT</th>
      <td>-51.375 ± 47.025 us<br>-2.25% ± 2.06%</td>
      <td>94.312 ± 100.083 us<br>0.95% ± 1.01%</td>
      <td>0.674 ± 0.317 ms<br>1.76% ± 0.83%</td>
    </tr>
    <tr>
      <th>Disc MC<br>Injected</th>
      <td>1.023 ± 0.055 ms<br>44.73% ± 2.52%</td>
      <td>4.831 ± 0.122 ms<br>48.75% ± 1.27%</td>
      <td>19.018 ± 0.468 ms<br>49.69% ± 1.25%</td>
    </tr>
    <tr>
      <th>Disc VT<br>Injected</th>
      <td>0.548 ± 0.057 ms<br>23.96% ± 2.51%</td>
      <td>2.966 ± 0.142 ms<br>29.94% ± 1.44%</td>
      <td>12.016 ± 0.291 ms<br>31.40% ± 0.77%</td>
    </tr>
    <tr>
      <th>Smart MC</th>
      <td>0.272 ± 0.047 ms<br>12.64% ± 2.17%</td>
      <td>1.094 ± 0.098 ms<br>11.37% ± 1.02%</td>
      <td>4.110 ± 0.476 ms<br>10.88% ± 1.27%</td>
    </tr>
    <tr>
      <th>Smart VT</th>
      <td>64.292 ± 34.243 us<br>2.98% ± 1.59%</td>
      <td>0.236 ± 0.105 ms<br>2.46% ± 1.09%</td>
      <td>0.765 ± 0.633 ms<br>2.03% ± 1.68%</td>
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
      <td>0.561 ± 0.393 us<br>10.06% ± 7.05%</td>
      <td>0.033 ± 0.053 us<br>1.61% ± 2.60%</td>
      <td>0.417 ± 0.301 us<br>7.47% ± 5.39%</td>
      <td>0.021 ± 0.055 us<br>1.06% ± 2.79%</td>
    </tr>
    <tr>
      <th scope="row">Disc VT</th>
      <td>0.882 ± 0.012 ms<br>15801.46% ± 627.69%</td>
      <td>8.054 ± 0.102 us<br>398.84% ± 7.91%</td>
      <td>0.885 ± 0.008 ms<br>15850.21% ± 497.23%</td>
      <td>11.486 ± 0.092 us<br>581.20% ± 12.48%</td>
    </tr>
    <tr>
      <th scope="row">Smart MC</th>
      <td>0.667 ± 1.217 us<br>4.00% ± 7.30%</td>
      <td>0.053 ± 0.187 us<br>0.47% ± 1.67%</td>
      <td>0.458 ± 0.593 us<br>3.09% ± 4.00%</td>
      <td>-0.064 ± 0.079 us<br>-0.66% ± 0.82%</td>
    </tr>
    <tr>
      <th scope="row">Smart VT</th>
      <td>0.419 ± 0.008 ms<br>2516.69% ± 122.76%</td>
      <td>7.905 ± 0.239 us<br>70.90% ± 2.32%</td>
      <td>0.426 ± 0.006 ms<br>2873.94% ± 83.54%</td>
      <td>11.576 ± 0.214 us<br>120.26% ± 2.34%</td>
    </tr>
  </tbody>
</table>
