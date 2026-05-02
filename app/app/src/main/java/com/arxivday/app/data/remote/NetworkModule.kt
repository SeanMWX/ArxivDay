package com.arxivday.app.data.remote

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

const val DEFAULT_API_BASE_URL = "https://api.seanzou.com"
const val DEFAULT_API_KEY = "1f97c6f038577cc0c4eed7b9ec4ce97af05de320f361f28912c3a6a5643b5f9e"

object NetworkModule {

    private var baseUrl: String = "$DEFAULT_API_BASE_URL/"
    private var apiKey: String = DEFAULT_API_KEY
    private var retrofit: Retrofit? = null
    private var apiService: ArxivApiService? = null

    fun setBaseUrl(url: String) {
        val trimmed = url.trim().ifBlank { DEFAULT_API_BASE_URL }
        val withScheme = if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
            trimmed
        } else {
            "https://$trimmed"
        }
        val normalized = if (withScheme.endsWith("/")) withScheme else "$withScheme/"
        if (normalized != baseUrl) {
            baseUrl = normalized
            retrofit = null
            apiService = null
        }
    }

    fun setApiKey(key: String) {
        val normalized = key.trim().ifBlank { DEFAULT_API_KEY }
        if (normalized != apiKey) {
            apiKey = normalized
            retrofit = null
            apiService = null
        }
    }

    private fun buildRetrofit(): Retrofit {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val client = OkHttpClient.Builder()
            .addInterceptor { chain ->
                val requestBuilder = chain.request().newBuilder()
                if (apiKey.isNotBlank()) {
                    requestBuilder.header("X-API-Key", apiKey)
                }
                chain.proceed(requestBuilder.build())
            }
            .addInterceptor(logging)
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .build()

        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    fun getApiService(): ArxivApiService {
        if (apiService == null) {
            retrofit = buildRetrofit()
            apiService = retrofit!!.create(ArxivApiService::class.java)
        }
        return apiService!!
    }
}
