# Grunt configuration updated to latest Grunt.  That means your minimum
# version necessary to run these tasks is Grunt 0.4.
#
# Please install this locally and install `grunt-cli` globally to run.
module.exports = (grunt) ->

    # Initialize the configuration.
    grunt.initConfig

        pkg: grunt.file.readJSON('package.json')

        meta:
            banner: '/**\n' +
                ' * <%= pkg.name %> - v<%= pkg.version %> - <%= grunt.template.today("yyyy-mm-dd") %>\n' +
                ' * <%= pkg.homepage %>\n' +
                ' *\n' +
                ' * Copyright (c) <%= grunt.template.today("yyyy") %> <%= pkg.author %>\n' +
                ' * Licensed <%= pkg.licenses.type %> <<%= pkg.licenses.url %>>\n' +
                ' */\n'

        cssmin:
            autotranslate:
                files: [
                    expand: true
                    cwd: 'stylesheets'
                    src: [
                        '**/*.css'
                    ]
                    ext: '.min.css'
                    dest: 'stylesheets'
                ]
        uglify:
            autotranslate:
                files: [
                    expand: true
                    cwd: 'javascripts'
                    src: ['**/*.js']
                    dest: 'javascripts'
                ]

    # Load external Grunt task plugins.
    grunt.loadNpmTasks 'grunt-contrib-cssmin'
    grunt.loadNpmTasks 'grunt-contrib-uglify'

    # configure the build task
    grunt.registerTask 'build', [
        'cssmin'
        'uglify'
    ]

    # Default task.
    grunt.registerTask 'default', [
        'build'
    ]
