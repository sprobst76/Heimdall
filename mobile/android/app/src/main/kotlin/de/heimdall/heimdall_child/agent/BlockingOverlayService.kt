package de.heimdall.heimdall_child.agent

import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.IBinder
import android.provider.Settings
import android.util.Log
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class BlockingOverlayService : Service() {
    companion object {
        private const val TAG = "HeimdallBlock"
        var instance: BlockingOverlayService? = null
            private set
    }

    private var windowManager: WindowManager? = null
    private var overlayView: View? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        Log.i(TAG, "Blocking overlay service created")
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val packageName = intent?.getStringExtra("packageName") ?: ""
        val groupId = intent?.getStringExtra("groupId") ?: ""
        showBlock(packageName, groupId)
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        hideBlock()
        instance = null
        super.onDestroy()
        Log.i(TAG, "Blocking overlay service destroyed")
    }

    fun showBlock(packageName: String, groupId: String) {
        if (!Settings.canDrawOverlays(this)) {
            Log.w(TAG, "No overlay permission")
            return
        }

        // Remove existing overlay if any
        hideBlock()

        val appLabel = try {
            val appInfo = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(appInfo).toString()
        } catch (e: Exception) {
            packageName
        }

        val groupLabel = when (groupId) {
            "streaming" -> "Streaming"
            "social" -> "Soziale Medien"
            "browser" -> "Browser"
            "gaming" -> "Spiele"
            else -> groupId
        }

        overlayView = createBlockView(appLabel, groupLabel)

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.OPAQUE
        )

        try {
            windowManager?.addView(overlayView, params)
            Log.i(TAG, "Overlay shown for $packageName ($groupId)")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to show overlay", e)
        }
    }

    fun hideBlock() {
        overlayView?.let {
            try {
                windowManager?.removeView(it)
            } catch (e: Exception) {
                Log.w(TAG, "Failed to remove overlay", e)
            }
        }
        overlayView = null
    }

    private fun createBlockView(appLabel: String, groupLabel: String): View {
        val dp = { value: Int ->
            TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, value.toFloat(), resources.displayMetrics
            ).toInt()
        }

        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.parseColor("#1A1A2E"))
            setPadding(dp(32), dp(64), dp(32), dp(64))

            // Shield icon (Unicode)
            addView(TextView(context).apply {
                text = "\uD83D\uDEE1\uFE0F"  // Shield emoji
                textSize = 72f
                gravity = Gravity.CENTER
                setPadding(0, 0, 0, dp(24))
            })

            // Title
            addView(TextView(context).apply {
                text = "App gesperrt"
                setTextColor(Color.WHITE)
                textSize = 28f
                typeface = Typeface.DEFAULT_BOLD
                gravity = Gravity.CENTER
                setPadding(0, 0, 0, dp(16))
            })

            // Message
            addView(TextView(context).apply {
                text = "\"$appLabel\" ist gerade nicht erlaubt."
                setTextColor(Color.parseColor("#B0B0CC"))
                textSize = 18f
                gravity = Gravity.CENTER
                setPadding(0, 0, 0, dp(8))
            })

            // Group info
            addView(TextView(context).apply {
                text = "Kategorie: $groupLabel"
                setTextColor(Color.parseColor("#8888AA"))
                textSize = 14f
                gravity = Gravity.CENTER
                setPadding(0, 0, 0, dp(48))
            })

            // Info text
            addView(TextView(context).apply {
                text = "Erledige Quests, um Bildschirmzeit\nfür diese Kategorie freizuschalten!"
                setTextColor(Color.parseColor("#9999BB"))
                textSize = 15f
                gravity = Gravity.CENTER
                setPadding(0, 0, 0, dp(48))
            })

            // Back to Heimdall button
            addView(Button(context).apply {
                text = "Zurück zu Heimdall"
                setTextColor(Color.WHITE)
                textSize = 16f
                typeface = Typeface.DEFAULT_BOLD
                isAllCaps = false

                background = GradientDrawable().apply {
                    setColor(Color.parseColor("#4F46E5"))
                    cornerRadius = dp(28).toFloat()
                }

                setPadding(dp(32), dp(16), dp(32), dp(16))

                setOnClickListener {
                    // Open Heimdall app
                    val launchIntent = packageManager.getLaunchIntentForPackage(
                        "de.heimdall.heimdall_child"
                    )
                    if (launchIntent != null) {
                        launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        startActivity(launchIntent)
                    }
                    hideBlock()
                }
            })
        }
    }
}
