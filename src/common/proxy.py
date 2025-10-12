class ContextProxy:
  """
  A proxy for a context object that will be initialized later. This allows modules to import the proxy instance (`log`, `config`) directly, and it will automatically forward calls to the real object once `init()` is called.
  一个上下文对象的代理，该对象将在稍后被初始化。这允许模块直接导入代理实例（`log`、`config`），并在 `init()` 被调用后，它会自动将调用转发给真实的对象。
  """
  _instance = None

  def set_instance(self, instance):
    """
    Called by the init function to inject the real, configured object.
    由 init 函数调用，以注入真实的、已配置的对象。
    """
    self._instance = instance

  def __getattr__(self, name):
    """
    Magic method that intercepts attribute access (e.g., `log.info`).
    拦截属性访问的魔法方法（例如 `log.info`）。
    It forwards the access to the real instance.
    它将访问请求转发给真实的实例。
    """
    if self._instance is None:
      # This error will be raised if you try to use log or config before calling init().
      # 如果您在调用 init() 之前尝试使用 log 或 config，将会引发此错误。
      raise RuntimeError("The application context has not been initialized. Please call 'init()' first.")
    return getattr(self._instance, name)
