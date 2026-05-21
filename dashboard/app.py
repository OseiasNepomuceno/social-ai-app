{% extends "base.html" %}

{% block title %}
Agendamentos
{% endblock %}

{% block extra_css %}

<style>

    .posts-grid {

        display: grid;

        grid-template-columns: repeat(
            auto-fit,
            minmax(320px, 1fr)
        );

        gap: 20px;

        margin-top: 20px;

    }

    .post-card {

        background: white;

        border-radius: 14px;

        padding: 18px;

        box-shadow: 0 2px 10px rgba(0,0,0,0.08);

    }

    .post-image {

        width: 100%;

        border-radius: 10px;

        margin-bottom: 15px;

    }

    .post-title {

        font-size: 18px;

        font-weight: bold;

        margin-bottom: 10px;

    }

    .post-content {

        white-space: pre-wrap;

        margin-bottom: 15px;

        color: #444;

    }

    .post-info {

        font-size: 14px;

        color: #666;

        margin-bottom: 6px;

    }

    .status {

        display: inline-block;

        padding: 5px 10px;

        border-radius: 20px;

        font-size: 12px;

        font-weight: bold;

        margin-top: 10px;

    }

    .pendente {

        background: #fff3cd;

        color: #856404;

    }

    .executado {

        background: #d4edda;

        color: #155724;

    }

    .erro {

        background: #f8d7da;

        color: #721c24;

    }

    .delete-btn {

        display: inline-block;

        margin-top: 15px;

        background: #ff4d4d;

        color: white;

        padding: 10px 14px;

        border-radius: 8px;

        text-decoration: none;

        font-size: 14px;

    }

    .delete-btn:hover {

        opacity: 0.9;

    }

</style>

{% endblock %}

{% block content %}

<h1>📅 Agendamentos</h1>

{% if erro %}

    <div style="
        background:#f8d7da;
        color:#721c24;
        padding:10px;
        border-radius:8px;
        margin-bottom:20px;
    ">

        {{ erro }}

    </div>

{% endif %}

<div class="posts-grid">

    {% for post in posts %}

        <div class="post-card">

            {% if post.imagem_url %}

                <img
                    src="{{ post.imagem_url }}"
                    class="post-image"
                >

            {% endif %}

            <div class="post-title">

                {{ post.tema }}

            </div>

            <div class="post-content">

                {{ post.conteudo }}

            </div>

            <div class="post-info">

                🌐 Rede:
                {{ post.rede }}

            </div>

            <div class="post-info">

                🎯 Nicho:
                {{ post.nicho }}

            </div>

            <div class="post-info">

                🚀 Modo:
                {{ post.modo }}

            </div>

            <div class="post-info">

                📅 Data:
                {{ post.data_postagem }}

            </div>

            <div class="post-info">

                ⏰ Hora:
                {{ post.hora_postagem }}

            </div>

            <div class="
                status
                {{ post.status }}
            ">

                {{ post.status }}

            </div>

            <br>

            <a
                href="/deletar/{{ post.id }}"
                class="delete-btn"
                onclick="return confirm('Deseja excluir este post?')"
            >
                🗑️ Excluir
            </a>

        </div>

    {% endfor %}

</div>

{% endblock %}
