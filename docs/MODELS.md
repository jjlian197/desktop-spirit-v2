# Live2D Model Setup

## Official Sample Models

Live2D provides free sample models for development:

### Download Sample Models

Visit: https://www.live2d.com/en/learn/sample/

Recommended models for Sherry:
- **Hiyori Momose** - Full body, expressions, physics
- **Haru** - Receptionist character, outfit changes
- **Epsilon** - Simple, beginner-friendly
- **Kei** - Motion-sync (lip-sync) support

## Model Structure

After downloading, extract the `runtime` folder contents:

```
src/assets/models/
└── hiyori/
    ├── hiyori.model3.json
    ├── hiyori.moc3
    ├── hiyori.physics3.json
    ├── hiyori.pose3.json
    ├── hiyori.cdi3.json
    ├── textures/
    │   ├── texture_00.png
    │   └── texture_01.png
    ├── motions/
    │   └── hiyori_m01.motion3.json
    └── expressions/
        └── f01.exp3.json
```

## Configuration

Update `config.yaml`:

```yaml
sprite:
  model:
    path: "src/assets/models/hiyori"
    default_expression: "normal"
```

## Expression Mapping

Common expression names in Live2D models:

| Expression | File |
|------------|------|
| normal | f01.exp3.json |
| happy | f02.exp3.json |
| sad | f03.exp3.json |
| angry | f04.exp3.json |
| surprised | f05.exp3.json |

The `SetExpression()` function uses the exp3.json filename (without extension).

## Custom Models

To use your own Live2D model:

1. Export from Live2D Cubism Editor
2. Include `runtime` folder files
3. Ensure `.model3.json` is present
4. Copy to `src/assets/models/your_model/`
5. Update config.yaml path

## Troubleshooting

### Model not loading
- Check that `.model3.json` exists
- Verify file paths in config
- Check logs: `~/.sherry/sprite.log`

### Textures missing
- Ensure `textures/` folder is present
- Check texture paths in `.model3.json`

### Performance issues
- Reduce texture size
- Disable physics if not needed
- Lower frame rate in code
