package de.heimdall.heimdall_child

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import de.heimdall.heimdall_child.agent.MethodChannelHandler

class MainActivity : FlutterActivity() {
    private var methodChannelHandler: MethodChannelHandler? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, MethodChannelHandler.CHANNEL_NAME)
        methodChannelHandler = MethodChannelHandler(applicationContext, channel)
        methodChannelHandler?.initialize()
    }

    override fun onDestroy() {
        methodChannelHandler?.destroy()
        super.onDestroy()
    }
}
