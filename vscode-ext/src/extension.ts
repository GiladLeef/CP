import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export function activate(context: vscode.ExtensionContext) {
    const provider = vscode.languages.registerCompletionItemProvider(
        { language : "c+"},
        {
            provideCompletionItems(document, position) {
                const completionItems: vscode.CompletionItem[] = [];
            
                const f_print = new vscode.CompletionItem('print', vscode.CompletionItemKind.Function);
                f_print.detail = 'A declaration of printf';
                f_print.insertText = new vscode.SnippetString('print("$1");');
                completionItems.push(f_print);

                const f_write = new vscode.CompletionItem('write', vscode.CompletionItemKind.Function);
                f_write.detail = 'A declaration of write';
                f_write.insertText = new vscode.SnippetString('write($1, "$2", $3);');
                completionItems.push(f_write);

                const f_exit = new vscode.CompletionItem('exit', vscode.CompletionItemKind.Function);
                f_exit.detail = 'A declaration of exit';
                f_exit.insertText = new vscode.SnippetString('exit($1);');
                completionItems.push(f_exit);

                const f_fork = new vscode.CompletionItem('fork', vscode.CompletionItemKind.Function);
                f_fork.detail = 'A declaration of fork';
                f_fork.insertText = new vscode.SnippetString('fork();');
                completionItems.push(f_fork);

                const f_execve = new vscode.CompletionItem('execve', vscode.CompletionItemKind.Function);
                f_execve.detail = 'A declaration of execve';
                f_execve.insertText = new vscode.SnippetString('execve("$1", $2, $3);');
                completionItems.push(f_execve);

                const f_malloc = new vscode.CompletionItem('malloc', vscode.CompletionItemKind.Function);
                f_malloc.detail = 'A declaration of malloc';
                f_malloc.insertText = new vscode.SnippetString('malloc($1);');
                completionItems.push(f_malloc);

                /*const f_free = new vscode.CompletionItem('free', vscode.CompletionItemKind.Function);
                f_print.detail = 'A declaration of free';
                f_print.insertText = new vscode.SnippetString('free($1);');
                completionItems.push(f_print);*/

                
                const snippet_main = new vscode.CompletionItem('main function', vscode.CompletionItemKind.Snippet);
                snippet_main.detail = 'Generate main function';
                snippet_main.insertText = new vscode.SnippetString('int main(){\n\t$1\n}');
                completionItems.push(snippet_main);
                
                const snippet_import = new vscode.CompletionItem('import', vscode.CompletionItemKind.Snippet);
                snippet_import.detail = 'Import something';
                snippet_import.insertText = new vscode.SnippetString('import $1.cp;');
                completionItems.push(snippet_import);
                


                const k_if          = new vscode.CompletionItem('if', vscode.CompletionItemKind.Keyword)
                k_if.detail         = 'keyword';
                k_if.insertText     = new vscode.SnippetString('if');
                completionItems.push(k_if)

                const k_else        = new vscode.CompletionItem('else', vscode.CompletionItemKind.Keyword)
                k_else.detail         = 'keyword';
                k_else.insertText     = new vscode.SnippetString('else');
                completionItems.push(k_else)

                const k_while       = new vscode.CompletionItem('while', vscode.CompletionItemKind.Keyword)
                k_while.detail         = 'keyword';
                k_while.insertText     = new vscode.SnippetString('while');
                completionItems.push(k_while)

                const k_do          = new vscode.CompletionItem('do', vscode.CompletionItemKind.Keyword)
                k_do.detail         = 'keyword';
                k_do.insertText     = new vscode.SnippetString('do');
                completionItems.push(k_do)

                const k_for         = new vscode.CompletionItem('for', vscode.CompletionItemKind.Keyword)
                k_for.detail         = 'keyword';
                k_for.insertText     = new vscode.SnippetString('for');
                completionItems.push(k_for)

                const k_return      = new vscode.CompletionItem('return', vscode.CompletionItemKind.Keyword)
                k_return.detail         = 'keyword';
                k_return.insertText     = new vscode.SnippetString('return');
                completionItems.push(k_return)

                const k_import      = new vscode.CompletionItem('import', vscode.CompletionItemKind.Keyword)
                k_import.detail         = 'keyword';
                k_import.insertText     = new vscode.SnippetString('import');
                completionItems.push(k_import)

                const k_new         = new vscode.CompletionItem('new', vscode.CompletionItemKind.Keyword)
                k_new.detail         = 'keyword';
                k_new.insertText     = new vscode.SnippetString('new');
                completionItems.push(k_new)

                const k_class       = new vscode.CompletionItem('class', vscode.CompletionItemKind.Keyword)
                k_class.detail         = 'keyword';
                k_class.documentation = 'keyword';
                k_class.insertText     = new vscode.SnippetString('class');
                completionItems.push(k_class)

                    

                const t_int         = new vscode.CompletionItem('int', vscode.CompletionItemKind.Struct)
                t_int.insertText     = new vscode.SnippetString('int');
                completionItems.push(t_int)

                const t_char        = new vscode.CompletionItem('char', vscode.CompletionItemKind.Struct)
                t_char.insertText     = new vscode.SnippetString('char');
                completionItems.push(t_char)

                const t_string      = new vscode.CompletionItem('string', vscode.CompletionItemKind.Struct)
                t_string.insertText     = new vscode.SnippetString('string');
                completionItems.push(t_string)

                const t_float       = new vscode.CompletionItem('float', vscode.CompletionItemKind.Struct)
                t_float.insertText     = new vscode.SnippetString('float');
                completionItems.push(t_float)

                const t_void        = new vscode.CompletionItem('void', vscode.CompletionItemKind.Struct)
                t_void.insertText     = new vscode.SnippetString('void');
                completionItems.push(t_void)
                    

                
                return completionItems;
            }
        },
    );

    context.subscriptions.push(provider);
}
