import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { isPremitive } from '@shared/functions/is-premitive.function';
import { TreeNode } from 'primeng/api';
import { TabsModule } from 'primeng/tabs';
import { TreeModule } from 'primeng/tree';

@Component({
  selector: 'app-inspect',
  imports: [TabsModule, TranslatePipe, TreeModule],
  templateUrl: './inspect.component.html',
  styleUrl: './inspect.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InspectComponent {
  /**
   * Inspect data
   */
  public readonly inspect = input.required<object>();

  /**
   * Inspect json value
   */
  protected readonly inspectJson = computed(() => {
    const inspect = this.inspect();
    if (inspect) {
      return JSON.stringify(inspect, null, 2).trim();
    }
    return null;
  });
  /**
   * Inspect tree value
   */
  protected readonly inspectTree = computed<TreeNode[]>(() => {
    const inspect = this.inspect();
    if (inspect) {
      const root = this.getTree(inspect, 'root');
      return root.children;
    }
    return [];
  });

  private getTree(value: unknown, key: string): TreeNode {
    if (isPremitive(value)) {
      return {
        label: key != null ? `${key}: ${String(value)}` : String(value),
        data: value,
        leaf: true,
      };
    }

    if (Array.isArray(value)) {
      return {
        label: key != null ? key : 'Array',
        data: value,
        children: value.map((item, index) => {
          const child = this.getTree(item, index.toString());
          return child;
        }),
        leaf: value.length === 0,
      };
    }

    const children: TreeNode[] = Object.entries(value).map(([k, v]) =>
      this.getTree(v, k),
    );

    return {
      label: key,
      data: value,
      children,
      leaf: children.length === 0,
    };
  }
}
