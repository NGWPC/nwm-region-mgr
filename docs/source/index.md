---
html_theme.sidebar_secondary.remove:
sd_hide_title: true
---

<!-- CSS overrides on the homepage only -->
<style>
.bd-main .bd-content .bd-article-container {
  max-width: 70rem; /* Make homepage a little wider instead of 60em */
}
/* Extra top/bottom padding to the sections */
article.bd-article section {
  padding: 3rem 0 7rem;
}
/* Override all h1 headers except for the hidden ones */
h1:not(.sd-d-none) {
  font-weight: bold;
  font-size: 48px;
  text-align: center;
  margin-bottom: 4rem;
}
/* Override all h3 headers that are not in hero */
h3:not(#hero h3) {
  font-weight: bold;
  text-align: center;
}
</style>

(homepage)=
# ngen-regionalization: Formulation and parameter regionalization for NextGen

<div id="hero">

<div id="hero-left">  <!-- Start Hero Left -->
  <h2 style="font-size: 60px; font-weight: bold; margin: 2rem auto 0;">ngen-regionalization</h2>
  <h3 style="font-weight: bold; margin-top: 0;">Formulation and parameter regionalization for NextGen</h3>
  <p>ngen-regionalization is a Python package for identifying optimal model formulations and parameters for ungauged catchments.</p>

<div class="homepage-button-container">
  <div class="homepage-button-container-row">
      <a href="./user_guide.html" class="homepage-button primary-button">User Guide</a>
      <a href="./faq.html" class="homepage-button secondary-button">See FAQ</a>
  </div>
  <div class="homepage-button-container-row">
      <a href="./API/index.html" class="homepage-button-link">See API Reference →</a>
  </div>
</div>
</div>  <!-- End Hero Left -->

<div id="hero-right">  <!-- Start Hero Right -->

<img src="./_images/overview.png" alt="Overview">

<!-- grid ended above, do not put anything on the right of markdown closings -->

</div>  <!-- End Hero Right -->
</div>  <!-- End Hero -->

----

<!-- Keep in markdown to generate headerlink -->
# Role in the NWM Ecosystem

<div id="hero">

<div id="hero-left">  <!-- Start Hero Left -->

<img src="./_images/framework.png" alt="framework">

<!-- grid ended above, do not put anything on the right of markdown closings -->

</div>  <!-- End Hero Left -->

<div id="hero-right">  <!-- Start Hero Right -->
  <h3 style="font-weight: bold; margin-top: 0;">A critical tool for forecast skill</h3>
  <p>Hydrologic models benefit strongly from calibration. Tools in this repository
  make the most out of limited observational data by intelligently transferring optimal
  parameter sets beyond calibrated catchments.</p>

</div>  <!-- End Hero Right -->

</div>  <!-- End Hero -->

# Key Features

:::::{grid} 1 1 2 2
:gutter: 5

::::{grid-item-card}
:shadow: none
:class-card: sd-border-0

:::{image} _static/index/formulation.svg
:::

:::{div} key-features-text
<strong>Formulation Regionalization</strong><br/>
Ranks NextGen model formulation suitability in ungauged catchments using comparisons to similar gauged catchments.
:::
::::

::::{grid-item-card}
:shadow: none
:class-card: sd-border-0

:::{image} _static/index/parameterization.svg
:::

:::{div} key-features-text
<strong>Parameterization Regionalization</strong><br/>
Estimates parameter values for ungauged catchments by leveraging calibrations from similar gauged catchments.
:::
::::

::::{grid-item-card}
:shadow: none
:class-card: sd-border-0

:::{image} _static/index/cluster.svg
:::

:::{div} key-features-text
<strong>Clustering</strong><br/>
Multiple methods available to group calibrated catchments into clusters based on shared hydrologic characteristics.
:::
::::

::::{grid-item-card}
:shadow: none
:class-card: sd-border-0

:::{image} _static/index/diagnostic.svg
:::

:::{div} key-features-text
<strong>Diagnostic Plots</strong><br/>
Generates plots and maps that explain why specific formulations and parameters were chosen.
:::
::::

::::{grid-item-card}
:shadow: none
:class-card: sd-border-0

:::{image} _static/index/scale.svg
:::

:::{div} key-features-text
<strong>Scalable</strong><br/>
Efficiently allocates computational resources to handle workflows from small watersheds up to CONUS-wide analyses.
:::
::::

::::{grid-item-card}
:shadow: none
:class-card: sd-border-0

:::{image} _static/index/config.svg
:::

:::{div} key-features-text
<strong>Customizable</strong><br/>
Gives users full control over every step through easily editable configuration files.
:::
::::
:::::

:::{toctree}
:maxdepth: 1
:hidden:

User Guide<user_guide.rst>
FAQ<faq.rst>
Config Builder<config_builder/index.rst>
API <API/index.rst>
:::
