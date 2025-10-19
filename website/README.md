# DataGenFlow Marketing Website

Marketing website and documentation for DataGenFlow.

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

Deploy the `dist/` folder to any static hosting:

- **GitHub Pages**: Push dist to gh-pages branch
- **Netlify**: Connect repo, build command `yarn build`, publish directory `dist`
- **Vercel**: Connect repo, framework preset `Vite`, output directory `dist`

## Project Structure

- `src/pages/` - Route pages (Landing, Docs)
- `src/components/` - React components organized by feature
- `src/lib/` - Utilities (docs fetching, types)
- `public/` - Static assets (copied from main repo via script)
- `scripts/` - Build scripts (copy-assets.js)

## Styling

- Tailwind CSS with custom green/black theme
- Some Primer React components for consistency with main app
- Responsive design (mobile-first)
