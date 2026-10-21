// SPIKE (delmir#43): Hermes rejects `import.meta` ("'import.meta' is currently unsupported"),
// and effect's ConfigProvider.fromEnv reads `import.meta?.env`. Replace the token with `{}`.
module.exports = function importMetaToEmptyObject({ types: t }) {
  return {
    name: 'import-meta-to-empty-object',
    visitor: {
      MetaProperty(path) {
        if (path.node.meta.name === 'import' && path.node.property.name === 'meta') {
          path.replaceWith(t.objectExpression([]));
        }
      },
    },
  };
};
