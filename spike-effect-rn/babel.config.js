module.exports = {
  presets: ['module:@react-native/babel-preset'],
  // SPIKE_NO_IMPORT_META=1 only for the offline check that shows the plugin is needed.
  plugins: process.env.SPIKE_NO_IMPORT_META ? [] : ['./babel-plugin-import-meta'],
};
