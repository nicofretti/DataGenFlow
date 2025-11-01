# DataGenFlow Website

Website and documentation for DataGenFlow.

## Requirements

- Node.js >= 20.0.0
- Yarn

## Development

```bash
yarn install
yarn dev
```

Visit http://localhost:5173

## Build

```bash
yarn build
```

Output in `dist/` directory.

## Deployment

Deploy the `dist/` on every merge into the `main` branch a GitHub Action is triggered to handle this. Currently it deploys to GitHub Pages.

## Project Structure

- `src/pages/` - Route pages (Landing, Docs)
- `src/components/` - React components organized by feature
- `src/lib/` - Utilities (docs fetching, types)
- `public/` - Static assets (copied from main repo via script)
- `scripts/` - Build scripts (copy-assets.js)

## Styling

- Tailwind CSS with custom green/black theme
