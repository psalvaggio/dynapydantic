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
      <td>0.395 ± 0.062 ms<br>17.05% ± 2.70%</td>
      <td>2.000 ± 0.134 ms<br>20.54% ± 1.39%</td>
      <td>7.664 ± 0.233 ms<br>20.27% ± 0.62%</td>
    </tr>
    <tr>
      <th>Disc VT</th>
      <td>-66.437 ± 68.103 us<br>-2.87% ± 2.94%</td>
      <td>0.258 ± 0.386 ms<br>2.65% ± 3.97%</td>
      <td>0.536 ± 0.460 ms<br>1.42% ± 1.22%</td>
    </tr>
    <tr>
      <th>Disc MC<br>Injected</th>
      <td>0.969 ± 0.059 ms<br>41.86% ± 2.74%</td>
      <td>4.766 ± 0.110 ms<br>48.96% ± 1.22%</td>
      <td>19.090 ± 1.050 ms<br>50.49% ± 2.78%</td>
    </tr>
    <tr>
      <th>Disc VT<br>Injected</th>
      <td>0.506 ± 0.079 ms<br>21.85% ± 3.47%</td>
      <td>3.030 ± 0.150 ms<br>31.13% ± 1.57%</td>
      <td>11.710 ± 0.435 ms<br>30.97% ± 1.16%</td>
    </tr>
    <tr>
      <th>Smart MC</th>
      <td>0.227 ± 0.050 ms<br>10.61% ± 2.36%</td>
      <td>1.023 ± 0.156 ms<br>10.73% ± 1.64%</td>
      <td>3.739 ± 0.565 ms<br>10.03% ± 1.52%</td>
    </tr>
    <tr>
      <th>Smart VT</th>
      <td>75.292 ± 46.989 us<br>3.52% ± 2.20%</td>
      <td>0.239 ± 0.168 ms<br>2.51% ± 1.76%</td>
      <td>0.673 ± 0.385 ms<br>1.80% ± 1.03%</td>
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
      <td>0.375 ± 0.428 us<br>6.72% ± 7.68%</td>
      <td>-0.054 ± 0.113 us<br>-2.59% ± 5.42%</td>
      <td>0.542 ± 0.358 us<br>10.24% ± 6.78%</td>
      <td>0.035 ± 0.143 us<br>1.76% ± 7.12%</td>
    </tr>
    <tr>
      <th scope="row">Disc VT</th>
      <td>0.881 ± 0.005 ms<br>15780.42% ± 801.06%</td>
      <td>8.024 ± 0.158 us<br>383.22% ± 20.03%</td>
      <td>0.887 ± 0.009 ms<br>16770.63% ± 939.10%</td>
      <td>12.034 ± 0.901 us<br>597.58% ± 59.00%</td>
    </tr>
    <tr>
      <th scope="row">Smart MC</th>
      <td>0.209 ± 1.503 us<br>1.22% ± 8.80%</td>
      <td>0.731 ± 0.261 us<br>6.50% ± 2.32%</td>
      <td>0.168 ± 2.180 us<br>1.11% ± 14.39%</td>
      <td>0.322 ± 0.802 us<br>3.29% ± 8.18%</td>
    </tr>
    <tr>
      <th scope="row">Smart VT</th>
      <td>0.385 ± 0.004 ms<br>2255.53% ± 184.26%</td>
      <td>8.728 ± 0.368 us<br>77.65% ± 3.37%</td>
      <td>0.392 ± 0.005 ms<br>2588.09% ± 348.78%</td>
      <td>12.925 ± 1.201 us<br>131.94% ± 14.03%</td>
    </tr>
  </tbody>
</table>
