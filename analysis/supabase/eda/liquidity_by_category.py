from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def find_input(root, name):
    output_dir = root / 'analysis' / 'supabase' / 'outputs'
    candidates = [
        output_dir / 'data' / name,
        output_dir / name,
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f'{name} not found. Checked: '
        + ', '.join(map(str, candidates))
    )


def summarize(group):
    values = group['liquidity_clob']
    valid = values.dropna()
    n = len(group)
    return pd.Series({
        'markets': n,
        'missing_or_invalid': values.isna().sum(),
        'coverage_pct': 100 * values.notna().sum() / n,
        'zero_count': valid.eq(0).sum(),
        'zero_pct_of_observed': 100 * valid.eq(0).mean() if len(valid) else np.nan,
        'median_liquidity': valid.median(),
        'q25_liquidity': valid.quantile(.25),
        'q75_liquidity': valid.quantile(.75),
        'mean_liquidity': valid.mean(),
        'p99_liquidity': valid.quantile(.99),
        'max_liquidity': valid.max(),
    })


def make_chart(summary, figure_path):
    from matplotlib.ticker import FuncFormatter, NullLocator
    plot = summary[summary['median_liquidity'].notna()].sort_values('median_liquidity', ascending=False)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13})
    fig = plt.figure(figsize=(16, 9), facecolor='white')
    ax = fig.add_axes([.31, .22, .40, .57])
    ax.set_facecolor('white')
    y = np.arange(len(plot))
    values = plot['median_liquidity'].to_numpy()
    colors = ['#0E7490' if name == 'Crypto' else '#D97706' if name == 'Sports'
              else '#94A3B8' if name == 'Other / Unclassified' else '#475569'
              for name in plot.index]
    if (values > 0).all():
        ax.set_xscale('log')
        ax.set_xlim(max(values.min() / 2.5, .001), values.max() * 2.0)
    else:
        ax.set_xscale('symlog', linthresh=1)
        ax.set_xlim(0, max(values.max() * 2, 2))
    for i in y:
        ax.axhline(i, color='#F1F5F9', linewidth=1, zorder=0)
    ax.scatter(values, y, s=115, c=colors, edgecolors='white', linewidths=1.3, zorder=3)
    ax.set_yticks(y, plot.index, fontsize=13, color='#334155')
    ax.set_ylim(len(plot) - .4, -.6)
    ax.tick_params(axis='y', length=0, pad=18)
    ax.tick_params(axis='x', length=0, pad=10, colors='#64748B')
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}' if x >= 1 else f'{x:g}'))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.grid(axis='x', color='#E2E8F0', linewidth=1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    scale_label = 'Log scale' if (values > 0).all() else 'Symlog scale (linear near zero)'
    ax.set_xlabel(f'Median liquidity · {scale_label}', labelpad=16, color='#64748B', fontsize=12)
    fig.text(.065, .915, 'Median Liquidity by Market Category', fontsize=27,
             weight='bold', color='#0F172A')
    fig.text(.065, .865, 'Median observed liquidity at collection time', fontsize=16, color='#64748B')
    fig.text(.065, .815, 'CATEGORY', fontsize=11, weight='bold', color='#64748B')
    fig.text(.81, .815, 'MEDIAN', fontsize=11, weight='bold', color='#64748B', ha='right')
    fig.text(.95, .815, 'COVERAGE', fontsize=11, weight='bold', color='#64748B', ha='right')
    for i, (name, row) in enumerate(plot.iterrows()):
        fy = fig.transFigure.inverted().transform(ax.transData.transform((values[i], i)))[1]
        fig.text(.81, fy, f"{row['median_liquidity']:,.2f}", va='center', ha='right',
                 fontsize=14, weight='bold', color=colors[i])
        fig.text(.95, fy, f"{row['coverage_pct']:.1f}%", va='center', ha='right',
                 fontsize=14, color='#475569')
    fig.text(.065, .105, 'Medians include zeros; missing and invalid liquidity excluded.', fontsize=11, color='#64748B')
    fig.text(.065, .07, 'Coverage = share of category markets with usable liquidity. Market status is not controlled.',
             fontsize=11, color='#64748B')
    fig.savefig(figure_path, dpi=200, facecolor='white')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--markets', type=Path)
    parser.add_argument('--categories', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    market_path = args.markets or find_input(root, 'market_sample_raw.csv')
    category_path = args.categories or find_input(root, 'market_category_sample.csv')
    output = args.output or root / 'analysis' / 'supabase' / 'outputs'

    markets = pd.read_csv(market_path, dtype={'slug': 'string'})
    categories = pd.read_csv(category_path, dtype={'slug': 'string'})
    for frame, required, name in [(markets, {'slug', 'liquidity_clob'}, 'market data'),
                                   (categories, {'slug', 'category'}, 'category labels')]:
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f'{name}: missing columns {sorted(missing)}. Available: {list(frame.columns)}')
        if frame['slug'].isna().any() or frame['slug'].duplicated().any():
            raise ValueError(f'{name}: slugs must be nonmissing and unique. Fix duplicates before joining.')

    df = markets.drop(columns=['category'], errors='ignore').merge(
        categories[['slug', 'category']], on='slug', how='left', validate='one_to_one', indicator=True)
    unmatched = df['_merge'].ne('both')
    blank = df['category'].fillna('').str.strip().eq('')
    unlabeled = unmatched | blank
    df.loc[unlabeled, 'category'] = 'Missing category label'
    print(f'Markets: {len(df):,}; without category labels: {unlabeled.sum():,}')
    if unlabeled.any():
        print('WARNING: Category labels do not cover every market. Check sample consistency before presenting.')

    raw = df['liquidity_clob']
    numeric = pd.to_numeric(raw, errors='coerce')
    invalid = numeric.notna() & (~np.isfinite(numeric) | numeric.lt(0))
    malformed = raw.notna() & numeric.isna()
    print(f'Missing input values: {raw.isna().sum():,}')
    print(f'Unparseable values: {malformed.sum():,}; negative/nonfinite values: {invalid.sum():,}')
    df['liquidity_clob'] = numeric.mask(invalid)
    if df.empty or df['liquidity_clob'].notna().sum() == 0:
        raise ValueError('No usable liquidity observations.')

    overall = summarize(df).to_frame().T
    summary = pd.DataFrame({name: summarize(group) for name, group in df.groupby('category')}).T
    summary.index.name = 'category'
    summary = summary.sort_values('median_liquidity', ascending=False, na_position='last')
    data_dir = output / 'data'
    fig_dir = output / 'figures'
    data_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    overall.to_csv(data_dir / 'liquidity_overall_summary.csv', index=False)
    summary.to_csv(data_dir / 'liquidity_by_category.csv')
    df.drop(columns='_merge').to_csv(data_dir / 'liquidity_market_sample.csv', index=False)
    print('\nOVERALL\n' + overall.round(2).to_string(index=False))
    print('\nBY CATEGORY\n' + summary.round(2).to_string())

    figure_path = fig_dir / 'liquidity_by_category.png'
    make_chart(summary, figure_path)
    print(f'\nSaved tables: {data_dir}\nSaved chart: {figure_path}')
    print('Interpret as a snapshot. Low liquidity may reflect market status; no causal claims.')


if __name__ == '__main__':
    main()
