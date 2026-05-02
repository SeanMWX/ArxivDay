package com.arxivday.app

import android.app.Application
import com.arxivday.app.data.local.AppDatabase

class ArxivDayApp : Application() {
    val database by lazy { AppDatabase.getInstance(this) }
}
