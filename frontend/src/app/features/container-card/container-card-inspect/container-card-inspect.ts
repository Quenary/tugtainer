import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { TreeNode } from 'primeng/api';
import { TabsModule } from 'primeng/tabs';
import { TreeModule } from 'primeng/tree';
import { IContainerInspectResult } from 'src/app/entities/containers/containers-interface';
import { isPremitive } from 'src/app/shared/functions/is-premitive.function';

@Component({
  selector: 'app-container-card-inspect',
  imports: [TabsModule, TranslatePipe, TreeModule],
  templateUrl: './container-card-inspect.html',
  styleUrl: './container-card-inspect.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerCardInspect {
  /**
   * Container info
   */
  public readonly inspect = input.required<IContainerInspectResult>();

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

    const children: TreeNode[] = Object.entries(value).map(([k, v]) => this.getTree(v, k));

    return {
      label: key,
      data: value,
      children,
      leaf: children.length === 0,
    };
  }
}
